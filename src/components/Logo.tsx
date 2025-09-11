import logoImage from "@/assets/logo.png";
import neoDSPMValidatorLogo from "@/assets/neoDSPMValidatorAgent.png"

interface LogoProps {
  className?: string;
}

const Logo = ({ className }: LogoProps) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <img src={neoDSPMValidatorLogo} alt="neoDSPMLogo" className="h-auto w-auto" />
    </div>
  );
};

export default Logo;