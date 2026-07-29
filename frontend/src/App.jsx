import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, clearLawzicSession, clearToken, getToken } from "./api/client";
import ContractWorkspacePage from "./pages/ContractWorkspacePage";
import HomePage from "./pages/HomePage";
import LegalConsultationPage from "./pages/LegalConsultationPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";

function ProtectedRoute({ user, children }) {
  const location = useLocation();
  return user
    ? children
    : <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }}/>;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(Boolean(getToken()));
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!getToken()) {
      setChecking(false);
      return;
    }
    api("/auth/me")
      .then(setUser)
      .catch(() => {
        clearToken();
        setUser(null);
      })
      .finally(() => setChecking(false));
  }, []);

  const showHome = () => {
    if (location.pathname === "/") {
      window.location.reload();
      return;
    }
    navigate("/");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const logout = () => {
    clearToken();
    setUser(null);
    navigate("/", { replace: true });
  };

  const deleteAccount = async password => {
    await api("/auth/me", {
      method: "DELETE",
      body: JSON.stringify({ password }),
    });
    clearLawzicSession();
    setUser(null);
    navigate("/", { replace: true });
  };

  if (checking) {
    return <main className="loading-screen"><p className="brand-logo">LAW<span>Z</span>IC</p><span>사용자 정보를 확인하고 있습니다.</span></main>;
  }

  return <Routes>
    <Route path="/" element={<HomePage
      user={user}
      onHome={showHome}
      onStart={() => navigate(user ? "/contracts" : "/login", { state: { from: "/contracts" } })}
      onConsultation={() => navigate(user ? "/legal-consultation" : "/login", { state: { from: "/legal-consultation" } })}
    />}/>
    <Route path="/login" element={user
      ? <Navigate to={location.state?.from || "/contracts"} replace/>
      : <LoginPage
          onHome={showHome}
          onSignup={() => navigate("/signup")}
          onLogin={loggedInUser => {
            setUser(loggedInUser);
            navigate(location.state?.from || "/contracts", { replace: true });
          }}
        />
    }/>
    <Route path="/signup" element={user
      ? <Navigate to="/contracts" replace/>
      : <SignupPage onHome={showHome} onLogin={() => navigate("/login")}/>
    }/>
    <Route path="/contracts" element={<ProtectedRoute user={user}>
      <ContractWorkspacePage
        user={user}
        onHome={showHome}
        onLogout={logout}
        onConsultation={() => navigate("/legal-consultation")}
        onDeleteAccount={deleteAccount}
      />
    </ProtectedRoute>}/>
    <Route path="/contracts/:contractId/analysis" element={<ProtectedRoute user={user}>
      <ContractWorkspacePage
        user={user}
        onHome={showHome}
        onLogout={logout}
        onConsultation={() => navigate("/legal-consultation")}
        onDeleteAccount={deleteAccount}
      />
    </ProtectedRoute>}/>
    <Route path="/legal-consultation" element={<ProtectedRoute user={user}>
      <LegalConsultationPage
        user={user}
        onHome={showHome}
        onWorkspace={() => navigate("/contracts")}
        onLogout={logout}
        onDeleteAccount={deleteAccount}
      />
    </ProtectedRoute>}/>
    <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes>;
}
