import logoImage from "@/assets/logo.png";

interface LogoProps {
  className?: string;
}

const Logo = ({ className }: LogoProps) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <img src={logoImage} alt="neoDSPM" className="h-8 w-auto" />
      <div className="flex flex-col">
        <span className="text-xl font-bold text-neo-blue">neo</span>
        <span className="text-xs text-muted-foreground uppercase tracking-wider">
          Data Security Posture Management
        </span>
      </div>
    </div>
  );
};

export default Logo;