import { Routes, Route, Navigate } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute";
import DashboardLayout from "./components/DashboardLayout";

import Login from "./pages/Login";
import Register from "./pages/Register";

import Home from "./pages/customer/Home";
import Chat from "./pages/customer/Chat";
import Orders from "./pages/customer/Orders";
import Tickets from "./pages/customer/Tickets";
import Feedback from "./pages/customer/Feedback";
import Profile from "./pages/customer/Profile";

import AdminHome from "./pages/admin/AdminHome";
import Customers from "./pages/admin/Customers";
import AdminOrders from "./pages/admin/AdminOrders";
import AdminTickets from "./pages/admin/AdminTickets";
import AdminConversations from "./pages/admin/AdminConversations";
import AdminFaqs from "./pages/admin/AdminFaqs";

const customerLinks = [
  { to: "/", label: "Dashboard", icon: "◆", end: true },
  { to: "/chat", label: "AI Chat", icon: "💬" },
  { to: "/orders", label: "Orders", icon: "📦" },
  { to: "/tickets", label: "Tickets", icon: "🎫" },
  { to: "/feedback", label: "Feedback", icon: "★" },
  { to: "/profile", label: "Profile", icon: "⚙" },
];

const adminLinks = [
  { to: "/admin", label: "Overview", icon: "◆", end: true },
  { to: "/admin/customers", label: "Customers", icon: "👤" },
  { to: "/admin/orders", label: "Orders", icon: "📦" },
  { to: "/admin/tickets", label: "Tickets", icon: "🎫" },
  { to: "/admin/conversations", label: "Conversations", icon: "💬" },
  { to: "/admin/faqs", label: "Knowledge base", icon: "📚" },
];

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Customer dashboard */}
      <Route
        path="/*"
        element={
          <ProtectedRoute allow={["customer"]}>
            <DashboardLayout title="Customer Dashboard" links={customerLinks}>
              <Routes>
                <Route index element={<Home />} />
                <Route path="chat" element={<Chat />} />
                <Route path="orders" element={<Orders />} />
                <Route path="tickets" element={<Tickets />} />
                <Route path="feedback" element={<Feedback />} />
                <Route path="profile" element={<Profile />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </DashboardLayout>
          </ProtectedRoute>
        }
      />

      {/* Admin dashboard */}
      <Route
        path="/admin/*"
        element={
          <ProtectedRoute allow={["admin"]}>
            <DashboardLayout title="Admin Dashboard" links={adminLinks}>
              <Routes>
                <Route index element={<AdminHome />} />
                <Route path="customers" element={<Customers />} />
                <Route path="orders" element={<AdminOrders />} />
                <Route path="tickets" element={<AdminTickets />} />
                <Route path="conversations" element={<AdminConversations />} />
                <Route path="faqs" element={<AdminFaqs />} />
                <Route path="*" element={<Navigate to="/admin" replace />} />
              </Routes>
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
