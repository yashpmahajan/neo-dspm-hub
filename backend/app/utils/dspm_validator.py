import os
import json
import datetime
import logging
from typing import Dict, Any

from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # Remove leading fence line
        first_newline = t.find("\n")
        if first_newline != -1:
            t = t[first_newline + 1 :]
        # Remove trailing fence
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def _best_effort_json_parse(text: str):
    try:
        return json.loads(text)
    except Exception:
        # try to find JSON block
        start_obj = text.find("{")
        start_arr = text.find("[")
        starts = [p for p in [start_obj, start_arr] if p != -1]
        if not starts:
            return None
        start = min(starts)
        end_obj = text.rfind("}")
        end_arr = text.rfind("]")
        end = max(end_obj, end_arr)
        if end > start:
            snippet = text[start : end + 1]
            try:
                return json.loads(snippet)
            except Exception:
                return None
        return None


class DSPMValidator:
    def __init__(self, api_key: str | None = None):
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)

    def validate_client_results(
        self,
        client_result_path: str,
        ground_truth_path: str,
        pdf_output_path: str | None = None
    ) -> Dict[str, Any]:
        """
        Validate client scan results against ground truth using AI and optionally generate a PDF report.
        Returns the structured JSON validation result (ready for PDF generation).
        """
        if not os.path.exists(client_result_path):
            logging.error(f"❌ Client result file not found: {client_result_path}")
            return {}

        if not os.path.exists(ground_truth_path):
            logging.error(f"❌ Ground truth file not found: {ground_truth_path}")
            return {}

        with open(client_result_path, "r", encoding="utf-8") as f:
            client_result_content = f.read()

        with open(ground_truth_path, "r", encoding="utf-8") as f:
            ground_truth_content = f.read()

        prompt = (
            "You are a DSPM validation engine.\n"
            "You will be given two inputs:\n"
            "1. client_result.json – scan results from the Normalyze platform.\n"
            "2. groundTruthFile – raw test data with labeled entities.\n\n"
            "Your task: Revalidate the client results against the ground truth file.\n"
            "Rules:\n"
            "- Compare each entity type (datatype).\n"
            "- If detected counts match ground truth → status=MATCHED.\n"
            "- If fewer detections than ground truth → status=UNDER_DETECTED.\n"
            "- If more detections than ground truth → status=OVER_DETECTED.\n"
            "- If entity is in ground truth but not in client results → status=NOT_DETECTED.\n"
            "- If entity reported by client but not in ground truth → status=FALSE_POSITIVE.\n\n"
            "Return ONLY strict JSON. No code fences, no markdown, no comments.\n"
            "JSON schema required:\n"
            "{\n"
            "  \"validationSummary\": {\n"
            "    \"totalEntitiesInGroundTruth\": <number>,\n"
            "    \"totalEntitiesDetectedByClient\": <number>,\n"
            "    \"matchedEntities\": <number>,\n"
            "    \"underDetectedEntities\": <number>,\n"
            "    \"overDetectedEntities\": <number>,\n"
            "    \"notDetectedEntities\": <number>,\n"
            "    \"falsePositives\": <number>\n"
            "  },\n"
            "  \"entityValidation\": [\n"
            "    {\n"
            "      \"datatype\": \"<entity name>\",\n"
            "      \"groundTruthCount\": <number>,\n"
            "      \"clientDetectedCount\": <number>,\n"
            "      \"status\": \"MATCHED\" | \"UNDER_DETECTED\" | \"OVER_DETECTED\" | \"NOT_DETECTED\" | \"FALSE_POSITIVE\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Client Result JSON:\n" + client_result_content + "\n\n"
            "Ground Truth File:\n" + ground_truth_content + "\n"
        )

        try:
            # Prefer JSON-mode if supported; fallback otherwise
            response_content = None
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a DSPM validation specialist. Return strict JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1800,
                    temperature=0,
                    response_format={"type": "json_object"}
                )
                response_content = response.choices[0].message.content.strip()
            except Exception as e:
                logging.warning(f"JSON mode not available or failed ({e}); retrying without response_format.")
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a DSPM validation specialist. Return strict JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1800,
                    temperature=0
                )
                response_content = response.choices[0].message.content.strip()

            logging.debug(f"Raw AI response for DSPM validation: {response_content[:400]}...")

            # Clean possible code fences, then parse
            cleaned = _strip_code_fences(response_content)
            parsed_response = _best_effort_json_parse(cleaned)

            if isinstance(parsed_response, dict):
                if pdf_output_path:
                    self._generate_dspm_report(parsed_response, pdf_output_path)
                return parsed_response

            logging.error("❌ AI response was not valid JSON after cleaning.")
            return {"error": "Invalid JSON response from AI"}

        except Exception as e:
            logging.error(f"❌ Failed to validate client results with AI: {e}")
            return {}

    def _generate_dspm_report(self, validation_json: dict, output_path: str):
        """Generate a DSPM Validation PDF Report from validation results."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        doc = SimpleDocTemplate(output_path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Heading1"],
            alignment=1,
            fontSize=18,
            spaceAfter=20,
        )

        subtitle_style = ParagraphStyle(
            name="SubTitleStyle",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.grey,
            alignment=1,
            spaceAfter=20,
        )

        normal_style = styles["Normal"]

        # Title
        elements.append(Paragraph("DSPM Validation Report", title_style))
        elements.append(Paragraph("Generated on: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), subtitle_style))
        elements.append(Spacer(1, 20))

        # Validation Summary
        summary = validation_json.get("validationSummary", {})
        elements.append(Paragraph("<b>Validation Summary</b>", styles["Heading2"]))
        summary_table_data = [
            ["Total Entities (Ground Truth)", summary.get("totalEntitiesInGroundTruth", 0)],
            ["Total Entities (Client)", summary.get("totalEntitiesDetectedByClient", 0)],
            ["Matched Entities", summary.get("matchedEntities", 0)],
            ["Under Detected", summary.get("underDetectedEntities", 0)],
            ["Over Detected", summary.get("overDetectedEntities", 0)],
            ["Not Detected", summary.get("notDetectedEntities", 0)],
            ["False Positives", summary.get("falsePositives", 0)],
        ]

        summary_table = Table(summary_table_data, colWidths=[250, 150])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Detailed Validation Results Table
        elements.append(Paragraph("<b>Entity Validation Results</b>", styles["Heading2"]))
        entity_data = [["Entity", "Ground Truth Count", "Client Detected Count", "Status"]]
        for entity in validation_json.get("entityValidation", []):
            entity_data.append([
                entity.get("datatype", ""),
                str(entity.get("groundTruthCount", 0)),
                str(entity.get("clientDetectedCount", 0)),
                entity.get("status", "")
            ])

        entity_table = Table(entity_data, colWidths=[150, 120, 150, 100])
        entity_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(entity_table)
        elements.append(PageBreak())

        # Misclassifications & Remediation
        elements.append(Paragraph("<b>Misclassifications and Remediation Steps</b>", styles["Heading2"]))
        for entity in validation_json.get("entityValidation", []):
            status = entity.get("status", "")
            if status != "MATCHED":
                elements.append(Paragraph(f"<b>Entity:</b> {entity.get('datatype')}", normal_style))
                elements.append(Paragraph(f"<b>Issue:</b> {status}", normal_style))

                remediation_steps = []
                if status == "UNDER_DETECTED":
                    remediation_steps = [
                        "Expand regex or ML patterns to capture missed cases.",
                        "Add additional test samples for edge cases.",
                        "Re-run detection with updated logic."
                    ]
                elif status == "OVER_DETECTED":
                    remediation_steps = [
                        "Tighten regex to reduce false matches.",
                        "Add validation checks for stricter entity matching.",
                        "Exclude irrelevant substrings or partial matches."
                    ]
                elif status == "NOT_DETECTED":
                    remediation_steps = [
                        "Implement detection logic for missing entity type.",
                        "Verify entity is supported in scanning configuration.",
                        "Enhance training dataset or regex for this datatype."
                    ]
                elif status == "FALSE_POSITIVE":
                    remediation_steps = [
                        "Review detection logic to reduce noise.",
                        "Ensure entity definitions are precise.",
                        "Refine ML model or regex patterns to improve accuracy."
                    ]

                elements.append(Paragraph("<b>Remediation Steps:</b>", normal_style))
                for step in remediation_steps:
                    elements.append(Paragraph(f"- {step}", normal_style))
                elements.append(Spacer(1, 15))

        disclaimer_text = (
            "AI Disclaimer: This DSPM validation report was generated using AI-based analysis. "
            "The results are based on the provided test data and client scan results. "
            "They may contain inaccuracies. All detections and findings should be manually validated "
            "against the actual data for production use."
        )
        elements.append(PageBreak())
        elements.append(Paragraph(disclaimer_text, normal_style))

        doc.build(elements)
        logging.info(f"✅ DSPM Validation Report generated: {output_path}")
