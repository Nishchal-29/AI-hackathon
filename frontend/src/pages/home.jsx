// src/pages/home.jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  PieChart,
  Pie,
  Tooltip,
  Cell,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  LineChart,
  Line,
} from "recharts";

export const Home = () => {
  const [stateData, setStateData] = useState([]);
  const [yearData, setYearData] = useState([]);
  const [causeData, setCauseData] = useState([]);
  const [districtData, setDistrictData] = useState({});
  const [loading, setLoading] = useState(true);

  const API_BASE = "http://127.0.0.1:8000";

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [stateRes, yearRes, causeRes, districtRes] = await Promise.all([
          axios.get(`${API_BASE}/classify_by_state`),
          axios.get(`${API_BASE}/classify_by_year`),
          // axios.get(`${API_BASE}/classify_by_cause`),
          axios.get(`${API_BASE}/classify_by_district`),
        ]);

        const formatData = (obj) =>
          Object.entries(obj).map(([key, value]) => ({
            name: key,
            value: Number(value),
          }));

        setStateData(formatData(stateRes.data.data));
        setYearData(formatData(yearRes.data.data));
        // setCauseData(formatData(causeRes.data.data));
        setDistrictData(districtRes.data.data);
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const COLORS = [
    "#0088FE",
    "#00C49F",
    "#FFBB28",
    "#FF8042",
    "#A28EFF",
    "#FF6666",
    "#66CC99",
  ];

  if (loading) return <h2 className="text-center mt-10">Loading data...</h2>;

  // Custom tooltip for showing districts when hovering over a state
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const stateName = payload[0].name;
      const districts = districtData[stateName] || {};
      const districtEntries = Object.entries(districts);

      return (
        <div
          style={{
            background: "#fff",
            padding: "10px",
            border: "1px solid #ccc",
            borderRadius: "8px",
            minWidth: 180,
            boxShadow: "0 6px 18px rgba(0,0,0,0.08)",
          }}
        >
          <h4 style={{ marginBottom: "8px" }}>{stateName}</h4>
          {districtEntries.length > 0 ? (
            districtEntries.map(([district, count]) => (
              <div key={district}>
                {district}: <strong>{count}</strong>
              </div>
            ))
          ) : (
            <div>No district data</div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ padding: "40px", fontFamily: "Poppins, sans-serif", position: "relative", minHeight: "100vh" }}>
      <h1 style={{ textAlign: "center", marginBottom: "40px" }}>
        🪓 DGMS Accident Data Visualization
      </h1>

      {/* STATE WISE PIE CHART */}
      <section style={{ marginBottom: "60px" }}>
        <h2>📍 Accidents by State</h2>
        <ResponsiveContainer width="100%" height={400}>
          <PieChart>
            <Pie
              data={stateData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={150}
              label
            >
              {stateData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </section>

      {/* YEAR WISE LINE CHART */}
      <section style={{ marginBottom: "60px" }}>
        <h2>📅 Accidents by Year</h2>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={yearData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#8884d8" />
          </LineChart>
        </ResponsiveContainer>
      </section>

      {/* CAUSE WISE BAR CHART */}
      {/* <section>
        <h2>⚠️ Accidents by Cause</h2>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={causeData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#82ca9d" />
          </BarChart>
        </ResponsiveContainer>
      </section> */}

      {/* Floating Chatbot Button */}
      <Link to="/chat" aria-label="Open chat" style={floatingLinkStyle}>
        <div style={floatingButtonStyle}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" style={{ marginRight: 8 }}>
            <path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="#fff" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"></path>
          </svg>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", textAlign: "left" }}>
            <strong style={{ fontSize: 14, color: "#fff" }}>Chat with RAG Bot</strong>
            <small style={{ fontSize: 11, color: "rgba(255,255,255,0.9)" }}>Ask questions about accidents</small>
          </div>
        </div>
      </Link>
    </div>
  );
};

// Floating styles (kept separate for readability)
const floatingLinkStyle = {
  position: "fixed",
  right: 24,
  bottom: 24,
  zIndex: 9999,
  textDecoration: "none",
  display: "flex",
  alignItems: "center",
};

const floatingButtonStyle = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "12px 16px",
  background: "linear-gradient(135deg,#0066ff 0%, #00c2ff 100%)",
  borderRadius: 14,
  color: "#fff",
  boxShadow: "0 10px 30px rgba(3,102,214,0.18)",
  transform: "translateY(0)",
  transition: "transform 180ms ease, box-shadow 180ms ease",
  cursor: "pointer",
  minWidth: 220,
  justifyContent: "space-between",
  outline: "none",
  border: "none",
  // hover effect applied via inline JS (not possible), so we add :hover via global style below if desired
};

const badgeStyle = {
  background: "#ff4757",
  color: "#fff",
  borderRadius: 12,
  padding: "4px 8px",
  fontSize: 11,
  marginLeft: 12,
  boxShadow: "0 6px 18px rgba(255,71,87,0.18)",
};

// Optional: small CSS-in-JS to add hover/pulse effect using animation keyframes injected via style tag
const styleSheet = `
  @keyframes chat-pulse {
    0% { transform: translateY(0); box-shadow: 0 10px 30px rgba(3,102,214,0.18); }
    50% { transform: translateY(-6px); box-shadow: 0 18px 36px rgba(3,102,214,0.14); }
    100% { transform: translateY(0); box-shadow: 0 10px 30px rgba(3,102,214,0.18); }
  }
  .chat-floating { animation: chat-pulse 4s ease-in-out infinite; border: none; }
  .chat-floating:hover { transform: translateY(-6px) scale(1.02); box-shadow: 0 20px 40px rgba(3,102,214,0.2); }
`;

// inject stylesheet once
if (typeof document !== "undefined" && !document.getElementById("chat-floating-style")) {
  const s = document.createElement("style");
  s.id = "chat-floating-style";
  s.innerHTML = styleSheet;
  document.head.appendChild(s);
  // add css class to floatingButton via slight DOM manipulation
  // (we can't add it directly to style object), so use a short timeout to attach class
  setTimeout(() => {
    const el = document.querySelector('[aria-label="Open chat"] > div');
    if (el) el.classList.add("chat-floating");
  }, 50);
}