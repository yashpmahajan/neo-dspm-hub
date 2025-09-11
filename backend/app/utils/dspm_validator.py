import os
import json
import datetime
import logging
from typing import Dict, Any

from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, PageBreak, Image
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

 # Try this simplified version first to test if JSON parsing works:

        prompt = (
            "Input Test Data (Ground Truth):\n" + ground_truth_content + "\n\n"
            "API Scan Data (Client Results):\n" + client_result_content + "\n"  
            "You are an expert in report generation for Data Security Posture Management (DSPM) solutions.\n"
            "You will receive two sets of structured input:\n"
            "1. Input Test Data file (ground truth) containing sensitive entities.\n"
            "2. API Scan Data file (detected entities from the DSPM product).\n"
            "Your task is to analyze the data and create a professional, client-facing report structure.\n"
            "The report must always include the following sections:\n"
            "---\n"
            "Section 1 – Input Test Data Summary\n"
            "- STRICTLY include only sensitive/PII entity types. This includes Full Name, SSN, Credit Card, Phone, Email, Address, DOB, and similar identifiers.\n"
            "- Always treat 'Full Name' as sensitive PII and include it in summaries, comparisons, and validation.\n"
            "- Base sensitivity classification on standard PII/sensitive data definitions.\n"
            "Section 2 – API Scan Summary\n"
            "- Analyze the API scan results and extract each entity type with its count.\n"
            "- Calculate the total entities count.\n"
            "Section 3 – DSPM Comparison Results\n"
            "- Create high-level comparison metrics:\n"
            "  * Total Entities in Input\n"
            "  * Entities Detected by API\n"
            "  * Matched Entities (entities correctly detected)\n"
            "  * Missed Entities (False Negatives - in input but not detected)\n"
            "  * Extra Detected (False Positives - detected but not in input)\n"
            "  * Accuracy % (calculated as Matched / Total Input * 100)\n"
            "- Create entity-level breakdown comparing Input Count, API Count, Matched, Missed, Extra for each entity type.\n"
            "Section 4 – Validation Results (Detailed Entity Validation)\n"
            "- For each individual entity value found in either dataset, create validation entries with:\n"
            "  * Sequential number\n"
            "  * Entity name/value\n"
            "  * Whether it's sensitive (Yes for PII/sensitive data, No otherwise)\n"
            "  * Whether detected by scanner (Yes/No)\n"
            "  * Whether present in input data (Yes/No)\n"
            "  * Result status (PASS/FAIL)\n"
            "- Mark as PASS if both input and API agree on detection status.\n"
            "- Mark as FAIL if:\n"
            "  * Input contains it but API missed → FAIL (Missed Detection)\n"
            "  * API detected but input did not contain it → FAIL (False Positive)\n"
            "  * API flagged non-sensitive data as sensitive → FAIL (Incorrectly Flagged)\n"
            "Section 5 – Observations & Recommendations\n"
            "- Calculate and summarize overall accuracy percentage\n"
            "- Identify entity types with highest accuracy\n"
            "- Identify entity types with most false negatives (missed detections)\n"
            "- Identify entity types with most false positives (incorrect detections)\n"
            "- Provide specific, actionable recommendations for improvement\n"
            "---\n"
            "**Important Analysis Rules:**\n"
            "- Always analyze the complete datasets provided\n"
            "- Calculate all totals and percentages based on actual data\n"
            "- If an entity type exists in one dataset but not the other, include it with count = 0\n"
            "- Consider common sensitive data types: SSN, Credit Card, Phone, Email, Address, DOB, etc.\n"
            "- Base sensitivity classification on standard PII/sensitive data definitions\n"
            "- Provide actionable recommendations based on specific gaps identified\n"
            "- Use a clear, well-formatted PDF report with no more than two consecutive blank lines.\n"                                                                          
            "---\n"
            "**Critical Output Format Requirement:**\n"
            "You MUST return ONLY a valid JSON object with this exact structure (no markdown, no code fences, no explanatory text):\n"
            "{\n"
            "  \"section1_input_summary\": {\n"
            "    \"entities\": [\n"
            "      {\"type\": \"entity_type_name\", \"count\": number}\n"
            "    ],\n"
            "    \"total_entities\": number\n"
            "  },\n"
            "  \"section2_api_summary\": {\n"
            "    \"entities\": [\n"
            "      {\"type\": \"entity_type_name\", \"count\": number}\n"
            "    ],\n"
            "    \"total_entities\": number\n"
            "  },\n"
            "  \"section3_comparison\": {\n"
            "    \"high_level\": {\n"
            "      \"total_input\": number,\n"
            "      \"detected_by_api\": number,\n"
            "      \"matched\": number,\n"
            "      \"missed\": number,\n"
            "      \"extra\": number,\n"
            "      \"accuracy_percent\": number\n"
            "    },\n"
            "    \"entity_breakdown\": [\n"
            "      {\n"
            "        \"entity_type\": \"name\",\n"
            "        \"input_count\": number,\n"
            "        \"api_count\": number,\n"
            "        \"matched\": number,\n"
            "        \"missed\": number,\n"
            "        \"extra\": number\n"
            "      }\n"
            "    ]\n"
            "  },\n"
            "  \"section4_validation\": [\n"
            "    {\n"
            "      \"sr_no\": number,\n"
            "      \"entity_type\": \"type_name\",\n"
            "      \"entity_value\": \"actual_value_or_identifier\",\n"
            "      \"sensitive\": \"Yes\" or \"No\",\n"
            "      \"detected_by_scanner\": \"Yes\" or \"No\",\n"
            "      \"present_in_input\": \"Yes\" or \"No\",\n"
            "      \"result\": \"PASS\" or \"FAIL\",\n"
            "      \"failure_reason\": \"reason if FAIL, empty string if PASS\"\n"
            "    }\n"
            "  ],\n"
            "  \"section5_observations\": {\n"
            "    \"accuracy_percent\": number,\n"
            "    \"highest_accuracy_entities\": [\"entity_type1\", \"entity_type2\"],\n"
            "    \"most_false_negatives\": [\"entity_type1\", \"entity_type2\"],\n"
            "    \"most_false_positives\": [\"entity_type1\", \"entity_type2\"],\n"
            "    \"recommendations\": [\n"
            "      \"Specific actionable recommendation 1\",\n"
            "      \"Specific actionable recommendation 2\"\n"
            "    ]\n"
            "  }\n"
            "}\n"
            "---\n"
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
                    max_tokens=4000,  # Increased token limit
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
                    max_tokens=4000,  # Increased token limit
                    temperature=0
                )
                response_content = response.choices[0].message.content.strip()

            # DEBUG: Print the raw response
            print("=== RAW AI RESPONSE (first 2000 chars) ===")
            print(response_content[:2000])
            print("=== END RAW RESPONSE ===")

            # Clean possible code fences, then parse
            cleaned = _strip_code_fences(response_content)
            
            # DEBUG: Print cleaned response
            print("=== CLEANED RESPONSE (first 2000 chars) ===")
            print(cleaned[:2000])
            print("=== END CLEANED ===")

            # DEBUG: Check if it looks like JSON
            cleaned_trimmed = cleaned.strip()
            if not (cleaned_trimmed.startswith('{') and cleaned_trimmed.endswith('}')):
                print(f"=== ERROR: Response doesn't look like JSON ===")
                print(f"Starts with: {cleaned_trimmed[:50]}")
                print(f"Ends with: {cleaned_trimmed[-50:]}")
                
                # Try to find JSON within the response
                start_brace = cleaned.find('{')
                end_brace = cleaned.rfind('}')
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    print("=== ATTEMPTING TO EXTRACT JSON ===")
                    extracted_json = cleaned[start_brace:end_brace+1]
                    print(f"Extracted: {extracted_json[:200]}...")
                    try:
                        parsed_response = json.loads(extracted_json)
                        print("✅ Successfully parsed extracted JSON!")
                        if pdf_output_path:
                            self._generate_dspm_report(parsed_response, pdf_output_path)
                        return parsed_response
                    except Exception as json_e:
                        print(f"❌ Failed to parse extracted JSON: {json_e}")

            parsed_response = _best_effort_json_parse(cleaned)

            if isinstance(parsed_response, dict):
                print("✅ Successfully parsed JSON response!")
                if pdf_output_path:
                    self._generate_dspm_report(parsed_response, pdf_output_path)
                return parsed_response

            logging.error("❌ AI response was not valid JSON after cleaning.")
            logging.error(f"Response preview: {cleaned[:500]}")
            return {"error": "Invalid JSON response from AI", "raw_response": cleaned[:1000]}

        except Exception as e:
            logging.error(f"❌ Failed to validate client results with AI: {e}")
            return {}

    def _generate_dspm_report(self, validation_json: dict, output_path: str):
        """Generate a DSPM Validation PDF Report with 5 sections as per new requirements."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        doc = SimpleDocTemplate(output_path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
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

        # Add Neova Solutions logo to top right
        logo_path = os.path.join(os.path.dirname(__file__), '../assets/logos/neova_solutions.png')
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=2.2 * inch, height=1.1 * inch, kind='proportional')
            logo_img.hAlign = 'RIGHT'
            elements.append(logo_img)
            elements.append(Spacer(1, 10))

        # Title and header
        elements.append(Paragraph("DSPM AI Validation Report", title_style))
        created_date_style = ParagraphStyle(
            name="CreatedDateStyle",
            parent=styles["Normal"],
            fontSize=8,
            alignment=1,
            textColor=colors.grey,
            spaceAfter=10,
        )
        elements.append(Paragraph("Created on: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), created_date_style))
        elements.append(Spacer(1, 30))

        # Section 1: Input Test Data Summary
        elements.append(Paragraph("<b>Section 1 – Input Test Data Summary</b>", styles["Heading2"]))
        section1 = validation_json.get("section1_input_summary", {})
        
        input_table_data = [["Entity Type", "Count"]]
        for entity in section1.get("entities", []):
            input_table_data.append([entity.get("type", ""), str(entity.get("count", 0))])
        input_table_data.append(["Total Entities", str(section1.get('total_entities', 0))])
        
        input_table = Table(input_table_data, colWidths=[300, 80])
        input_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),  # Bold for total row
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ]))
        elements.append(input_table)
        elements.append(Spacer(1, 20))

        # Section 2: API Scan Summary
        elements.append(Paragraph("<b>Section 2 – API Scan Summary</b>", styles["Heading2"]))
        section2 = validation_json.get("section2_api_summary", {})
        
        api_table_data = [["Entity Type", "Count"]]
        for entity in section2.get("entities", []):
            api_table_data.append([entity.get("type", ""), str(entity.get("count", 0))])
        api_table_data.append(["Total Entities", str(section2.get('total_entities', 0))])
        
        api_table = Table(api_table_data, colWidths=[300, 80])
        api_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgreen),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),  # Bold for total row
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ]))
        elements.append(api_table)
        elements.append(Spacer(1, 20))

        # Section 3: DSPM Comparison Results
        elements.append(Paragraph("<b>Section 3 – DSPM Comparison Results</b>", styles["Heading2"]))
        section3 = validation_json.get("section3_comparison", {})
        high_level = section3.get("high_level", {})
        
        # High-level comparison table
        elements.append(Paragraph("<b>High-Level Comparison:</b>", styles["Heading3"]))
        comparison_table_data = [
            ["Metric", "Count"],
            ["Total Entities in Input", str(high_level.get("total_input", 0))],
            ["Entities Detected by API", str(high_level.get("detected_by_api", 0))],
            ["Matched Entities (Correct)", str(high_level.get("matched", 0))],
            ["Missed Entities", str(high_level.get("missed", 0))],
            ["Extra Detected (False Positives)", str(high_level.get("extra", 0))],
            ["Accuracy %", f"{high_level.get('accuracy_percent', 0):.1f}%"],
        ]
        
        comparison_table = Table(comparison_table_data, colWidths=[300, 80])
        comparison_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.orange),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),  # Bold for accuracy row
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, -1), (-1, -1), colors.yellow),
        ]))
        elements.append(comparison_table)
        elements.append(Spacer(1, 15))

        # Entity-level breakdown
        elements.append(Paragraph("<b>Entity-Level Breakdown:</b>", styles["Heading3"]))
        breakdown_data = [["Entity Type", "Input Count", "API Count", "Matched", "Missed", "Extra"]]
        for entity in section3.get("entity_breakdown", []):
            breakdown_data.append([
                entity.get("entity_type", ""),
                str(entity.get("input_count", 0)),
                str(entity.get("api_count", 0)),
                str(entity.get("matched", 0)),
                str(entity.get("missed", 0)),
                str(entity.get("extra", 0))
            ])
        
        breakdown_table = Table(breakdown_data, colWidths=[120, 60, 60, 60, 60, 60])
        breakdown_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightcyan),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(breakdown_table)
        elements.append(Spacer(1, 20))

        # Section 4: Validation Results (Detailed Entity Validation)
        elements.append(PageBreak())
        elements.append(Paragraph("<b>Section 4 – Validation Results (Detailed Entity Validation)</b>", styles["Heading2"]))
        
        validation_data = [["Sr. No", "Entity Type", "Entity Value", "Sensitive", "Detected", "In Input", "Result"]]
        validation_items = validation_json.get("section4_validation", [])
        
        for item in validation_items:
            entity_value = str(item.get("entity_value", ""))
            # Truncate long values for better display
            if len(entity_value) > 25:
                entity_value = entity_value[:22] + "..."
            
            validation_data.append([
                str(item.get("sr_no", "")),
                item.get("entity_type", ""),
                entity_value,
                item.get("sensitive", ""),
                item.get("detected_by_scanner", ""),
                item.get("present_in_input", ""),
                item.get("result", "")
            ])
        
        validation_table = Table(validation_data, colWidths=[50, 100, 120, 60, 60, 60, 60])
        
        # Create base table style
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.purple),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("TEXTCOLOR", (1, 1), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]
        
        # Add color coding for result column
        for i, item in enumerate(validation_items, 1):
            if item.get("result") == "PASS":
                table_style.append(("BACKGROUND", (6, i), (6, i), colors.lightgreen))
            else:
                table_style.append(("BACKGROUND", (6, i), (6, i), colors.lightcoral))
        
        validation_table.setStyle(TableStyle(table_style))
        elements.append(validation_table)
        elements.append(Spacer(1, 20))

        # Section 5: Observations & Recommendations
        elements.append(Paragraph("<b>Section 5 – Observations & Recommendations</b>", styles["Heading2"]))
        section5 = validation_json.get("section5_observations", {})
        
        elements.append(Paragraph(f"<b>Overall Accuracy:</b> {section5.get('accuracy_percent', 0):.1f}%", styles["Normal"]))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("<b>Highest Accuracy Entities:</b>", styles["Normal"]))
        for entity in section5.get("highest_accuracy_entities", []):
            elements.append(Paragraph(f"• {entity}", styles["Normal"]))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("<b>Most False Negatives:</b>", styles["Normal"]))
        for entity in section5.get("most_false_negatives", []):
            elements.append(Paragraph(f"• {entity}", styles["Normal"]))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("<b>Most False Positives:</b>", styles["Normal"]))
        for entity in section5.get("most_false_positives", []):
            elements.append(Paragraph(f"• {entity}", styles["Normal"]))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("<b>Recommendations:</b>", styles["Normal"]))
        for recommendation in section5.get("recommendations", []):
            elements.append(Paragraph(f"• {recommendation}", styles["Normal"]))
        elements.append(Spacer(1, 20))

        # Remove the disclaimer paragraph from the main content
        # doc.build will add the disclaimer only as a footer
        doc.build(elements, onFirstPage=self._add_footer, onLaterPages=self._add_footer)
        logging.info(f"✅ DSPM Validation Report generated: {output_path}")

    def _add_footer(self, canvas, doc):
        # Short, clear AI disclaimer for the footer
        footer_text = (
            "Disclaimer: This DSPM validation report was AI-generated based on test data and client scan results.\n"
            "Findings may contain inaccuracies and should be manually verified against actual data before production use."
        )
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        width, height = A4
        margin = 40
        canvas.setFillColorRGB(0.3, 0.3, 0.3)
        for i, line in enumerate(footer_text.split("\n")):
            canvas.drawString(margin, 20 + i * 10, line)
        canvas.restoreState()
