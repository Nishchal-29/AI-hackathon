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
  const [causeExamples, setCauseExamples] = useState({}); // NEW: store examples from backend
  const [districtData, setDistrictData] = useState({});
  const [loading, setLoading] = useState(true);

  const [expandedCategory, setExpandedCategory] = useState(null); // which category's examples to show expanded
  const API_BASE = "http://127.0.0.1:8000";

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [stateRes, yearRes, causeRes, districtRes] = await Promise.all([
          axios.get(`${API_BASE}/classify_by_state`),
          axios.get(`${API_BASE}/classify_by_year`),
          axios.get(`${API_BASE}/classify_by_cause`),
          axios.get(`${API_BASE}/classify_by_district`),
        ]);

        const formatData = (obj) =>
          Object.entries(obj).map(([key, value]) => ({
            name: key,
            value: Number(value),
          }));

        setStateData(formatData(stateRes.data.data));
        setYearData(formatData(yearRes.data.data));

        // ---- Handle cause response which may be rich (counts + examples) ----
        const causePayload = causeRes.data.data ?? {};
        // If API returned { counts: {...}, examples: {...} } use counts for chart
        const counts = causePayload.counts ?? causePayload; // if counts exists use it, else payload itself
        const examples = causePayload.examples ?? {};

        setCauseData(formatData(counts));
        setCauseExamples(examples);

        // --------------------------------------------------------------------
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

  // render a few example snippets for the category
  const renderExamplesPreview = (category) => {
    const ex = causeExamples[category] || [];
    if (!ex || ex.length === 0) return <div style={{ color: "#666" }}>No examples</div>;
    // show up to 2 snippets in preview
    return ex.slice(0, 2).map((e, i) => (
      <div key={i} style={{ marginBottom: 8, background: "#fafafa", padding: 8, borderRadius: 6 }}>
        <div style={{ fontSize: 12, color: "#333", whiteSpace: "pre-wrap" }}>
          {e.snippet || "(no snippet)"}
        </div>
        <div style={{ fontSize: 11, color: "#888", marginTop: 6 }}>row: {e.idx}</div>
      </div>
    ));
  };

  // expanded modal-like list of examples
  const ExpandedExamples = ({ category, onClose }) => {
    const ex = causeExamples[category] || [];
    return (
      <div style={expandedOverlayStyle} onClick={onClose}>
        <div style={expandedPanelStyle} onClick={(ev) => ev.stopPropagation()}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0 }}>{category} — Examples ({ex.length})</h3>
            <button onClick={onClose} style={smallCloseBtn}>Close</button>
          </div>
          <div style={{ marginTop: 12, maxHeight: "60vh", overflowY: "auto" }}>
            {ex.length === 0 && <div>No examples available</div>}
            {ex.map((e, i) => (
              <div key={i} style={{ marginBottom: 12, padding: 12, borderRadius: 8, background: "#fff", boxShadow: "0 4px 12px rgba(0,0,0,0.04)" }}>
                <div style={{ fontSize: 13, color: "#222", whiteSpace: "pre-wrap" }}>{e.snippet || "(no snippet)"}</div>
                <div style={{ fontSize: 12, color: "#666", marginTop: 8 }}>row: {e.idx}</div>
                {/* optional: show JSON for dev */}
                {/* <pre style={{fontSize:11, marginTop:8}}>{JSON.stringify(e.record, null, 2)}</pre> */}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: "40px", fontFamily: "Poppins, sans-serif", position: "relative", minHeight: "100vh" }}>
      <h1 style={{ textAlign: "center", marginBottom: "40px" }}>
        Mine Accident Data Visualization
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
      <section style={{ marginBottom: 20 }}>
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

        {/* Examples preview grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, marginTop: 18 }}>
          {causeData.length === 0 && <div style={{ color: "#666" }}>No cause data</div>}
          {causeData.map((c, idx) => (
            <div key={idx} style={{ padding: 12, borderRadius: 8, background: "#f7f9fb", boxShadow: "0 6px 18px rgba(2,6,23,0.03)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>{c.name}</strong>
                <div style={{ fontSize: 14, color: "#0366d6" }}>{c.value}</div>
              </div>
              <div style={{ marginTop: 8 }}>
                {renderExamplesPreview(c.name)}
              </div>
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                <button style={tinyBtn} onClick={() => setExpandedCategory(c.name)}>View all examples</button>
              </div>
            </div>
          ))}
        </div>
      </section>

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

      {expandedCategory && (
        <ExpandedExamples category={expandedCategory} onClose={() => setExpandedCategory(null)} />
      )}
    </div>
  );
};

// ---------- styles ----------
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
};

const tinyBtn = {
  padding: "6px 10px",
  borderRadius: 6,
  border: "1px solid #dce7ff",
  background: "#fff",
  cursor: "pointer",
  fontSize: 13,
};

const expandedOverlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.35)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 20000,
  padding: 20,
};

const expandedPanelStyle = {
  width: "min(1100px, 95%)",
  maxHeight: "90vh",
  background: "#fff",
  borderRadius: 12,
  padding: 20,
  boxShadow: "0 30px 80px rgba(2,6,23,0.2)",
  overflow: "hidden",
};

const smallCloseBtn = {
  padding: "6px 10px",
  borderRadius: 6,
  border: "1px solid #eee",
  background: "#f7f9fb",
  cursor: "pointer",
};