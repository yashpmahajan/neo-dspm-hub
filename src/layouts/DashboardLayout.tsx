import { Outlet } from "react-router-dom";
import Sidebar from "@/components/Sidebar";

const DashboardLayout = () => {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default DashboardLayout;