import { useState } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

/* ── Chart data ── */
const CHART_DATA = [
  { month:"Jan", amount:1200 }, { month:"Feb", amount:1800 },
  { month:"Mar", amount:1400 }, { month:"Apr", amount:2200 },
  { month:"May", amount:2800 }, { month:"Jun", amount:3200 },
  { month:"Jul", amount:4100 }, { month:"Aug", amount:7200 },
  { month:"Sep", amount:5100 }, { month:"Oct", amount:4400 },
  { month:"Nov", amount:5600 }, { month:"Dec", amount:4800 },
];

/* ── Stat cards ── */
const STATS = [
  { label:"Total Amount",       value:"$126,450", trend:"+15%", up:true  },
  { label:"Total Tuition",      value:"$67,200",  trend:"+15%", up:true  },
  { label:"Total Activities",   value:"$8,000",   trend:"-8%",  up:false },
  { label:"Total Miscellaneous",value:"$6,150",   trend:"-8%",  up:false },
];

/* ── Students fees ── */
const FEES = [
  { id:"2015-02-017", name:"Sophia Wilson",   class:"11A",           tuition:4500, activities:300, misc:200, amount:5000,  status:"Paid",    avatar:"SW", color:"#fce7f3", tc:"#be185d" },
  { id:"2015-01-016", name:"Ethan Lee",       class:"10B",           tuition:4500, activities:250, misc:150, amount:4900,  status:"Pending", avatar:"EL", color:"#dbeafe", tc:"#1d4ed8" },
  { id:"2015-03-012", name:"Michael Brown",   class:"12 AP Calculus",tuition:4800, activities:300, misc:200, amount:5300,  status:"Paid",    avatar:"MB", color:"#d1fae5", tc:"#065f46" },
  { id:"2015-01-019", name:"Ava Smith",       class:"9B",            tuition:4500, activities:250, misc:100, amount:4850,  status:"Overdue", avatar:"AS", color:"#fef3c7", tc:"#92400e" },
  { id:"2015-01-004", name:"Lucas Johnson",   class:"11A",           tuition:4500, activities:300, misc:200, amount:5000,  status:"Paid",    avatar:"LJ", color:"#ede9fe", tc:"#5b21b6" },
  { id:"2015-03-015", name:"Isabella Garcia", class:"8B",            tuition:4200, activities:200, misc:150, amount:4550,  status:"Pending", avatar:"IG", color:"#e0f2fe", tc:"#0369a1" },
  { id:"2016-02-008", name:"Liam Thompson",   class:"10B",           tuition:4500, activities:250, misc:200, amount:4950,  status:"Paid",    avatar:"LT", color:"#f0fdf4", tc:"#14532d" },
  { id:"2016-01-021", name:"Evelyn Mitchell", class:"10A",           tuition:4500, activities:300, misc:150, amount:4950,  status:"Overdue", avatar:"EM", color:"#fee2e2", tc:"#991b1b" },
  { id:"2014-02-022", name:"Alexander Perez", class:"12",            tuition:4800, activities:250, misc:200, amount:5250,  status:"Paid",    avatar:"AP", color:"#fce7f3", tc:"#be185d" },
  { id:"2017-01-019", name:"Harper Nelson",   class:"9B",            tuition:4200, activities:200, misc:100, amount:4500,  status:"Pending", avatar:"HN", color:"#dbeafe", tc:"#1d4ed8" },
];

const STATUS_STYLES = {
  Paid:    { color:"#0ea5e9", bg:"#e0f2fe"  },
  Pending: { color:"#f59e0b", bg:"#fef3c7"  },
  Overdue: { color:"#ef4444", bg:"#fee2e2"  },
};

const CLASSES  = ["All Classes","8B","9B","10A","10B","11A","12","12 AP Calculus"];
const STATUSES = ["All Status","Paid","Pending","Overdue"];
const PAGE_SIZE = 6;

/* ── Custom tooltip ── */
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="fc-tooltip">
      <div className="fc-tooltip-val">${payload[0].value.toLocaleString()}</div>
      <div className="fc-tooltip-date">{label} 19, 2030</div>
    </div>
  );
}

/* ── Mini sparkline icon ── */
function Sparkline() {
  return (
    <svg width="60" height="28" viewBox="0 0 60 28">
      <polyline points="0,20 12,14 24,18 36,8 48,12 60,6"
        fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}

export default function FeesCollection() {
  const [search,      setSearch]      = useState("");
  const [classFilter, setClassFilter] = useState("All Classes");
  const [statusFilter,setStatusFilter]= useState("All Status");
  const [selected,    setSelected]    = useState(new Set());
  const [page,        setPage]        = useState(1);

  const filtered = FEES.filter(f => {
    const matchSearch = f.name.toLowerCase().includes(search.toLowerCase()) || f.id.includes(search);
    const matchClass  = classFilter  === "All Classes" || f.class === classFilter;
    const matchStatus = statusFilter === "All Status"  || f.status === statusFilter;
    return matchSearch && matchClass && matchStatus;
  });

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated  = filtered.slice((page-1)*PAGE_SIZE, page*PAGE_SIZE);

  const toggleAll = () => selected.size === paginated.length
    ? setSelected(new Set())
    : setSelected(new Set(paginated.map(f => f.id)));

  const toggleOne = id => setSelected(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const handleSearch = v => { setSearch(v); setPage(1); };

  return (
    <div className="fc-root">

      {/* ── Top section: chart + stat cards ── */}
      <div className="fc-top">

        {/* Area chart */}
        <div className="fc-chart-card">
          <div className="fc-chart-header">
            <span className="fc-chart-title">Collecte des frais</span>
            <span className="fc-dots">···</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={CHART_DATA} margin={{ top:10, right:10, left:0, bottom:0 }}>
              <defs>
                <linearGradient id="fcGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#f0b429" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#f0b429" stopOpacity={0.02}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f3f7" vertical={false}/>
              <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill:"#9ca3af", fontSize:12 }}/>
              <YAxis domain={[0,7500]} ticks={[0,1000,2500,5000,7500]} axisLine={false} tickLine={false} tick={{ fill:"#9ca3af", fontSize:11 }}/>
              <Tooltip content={<ChartTooltip />} cursor={{ stroke:"#f0b429", strokeWidth:1, strokeDasharray:"4 4" }}/>
              <Area type="monotone" dataKey="amount" stroke="#f0b429" strokeWidth={2.5} fill="url(#fcGrad)" dot={false} activeDot={{ r:6, fill:"#f0b429", stroke:"white", strokeWidth:2 }}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Stat cards */}
        <div className="fc-stats">
          {STATS.map((s, i) => (
            <div key={i} className="fc-stat-card">
              <div className="fc-stat-top">
                <Sparkline />
                <span className={`fc-stat-trend ${s.up?"up":"down"}`}>
                  {s.up?"↑":"↓"} {s.trend}
                </span>
              </div>
              <div className="fc-stat-value">{s.value}</div>
              <div className="fc-stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Fees table ── */}
      <div className="fc-table-section">

        {/* Table header */}
        <div className="fc-table-header">
          <span className="fc-chart-title">Collecte des frais</span>
          <div className="fc-table-controls">
            {/* Search */}
            <div className="fc-search-box">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2">
                <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
              </svg>
              <input className="fc-search-input" placeholder="Rechercher par nom ou identifiant" value={search} onChange={e => handleSearch(e.target.value)}/>
            </div>
            {/* Date */}
            <div className="fc-filter-btn">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="2">
                <rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>
              </svg>
              Today
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="2.5"><path d="M6 9l6 6 6-6"/></svg>
            </div>
            {/* Class filter */}
            <select className="fc-select" value={classFilter} onChange={e=>{setClassFilter(e.target.value);setPage(1);}}>
              {CLASSES.map(c=><option key={c}>{c}</option>)}
            </select>
            {/* Status filter */}
            <select className="fc-select" value={statusFilter} onChange={e=>{setStatusFilter(e.target.value);setPage(1);}}>
              {STATUSES.map(s=><option key={s}>{s}</option>)}
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="fc-table-wrap">
          <table className="fc-table">
            <thead>
              <tr>
                <th style={{width:40}}>
                  <input type="checkbox" className="st-checkbox"
                    checked={selected.size===paginated.length && paginated.length>0}
                    onChange={toggleAll}/>
                </th>
                <th>Nom de l’élève</th>
                <th>Classe</th>
                <th>Frais de scolarité</th>
                <th>Frais d’activités</th>
                <th>Divers</th>
                <th>Montant</th>
                <th>Statut</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {paginated.map((f, i) => {
                const isChecked = selected.has(f.id);
                const st = STATUS_STYLES[f.status];
                return (
                  <tr key={f.id} className={isChecked?"row-selected": i%2===1?"row-alt":""}>
                    <td><input type="checkbox" className="st-checkbox" checked={isChecked} onChange={()=>toggleOne(f.id)}/></td>
                    <td>
                      <div className="fc-student-cell">
                        <div className="fc-avatar" style={{background:f.color, color:f.tc}}>{f.avatar}</div>
                        <div>
                          <div className="fc-student-name">{f.name}</div>
                          <div className="fc-student-id">{f.id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="fc-td">{f.class}</td>
                    <td className="fc-td">${f.tuition.toLocaleString()}</td>
                    <td className="fc-td">${f.activities}</td>
                    <td className="fc-td">${f.misc}</td>
                    <td className="fc-td fc-amount">${f.amount.toLocaleString()}</td>
                    <td>
                      <span className="fc-status" style={{color:st.color, background:st.bg}}>
                        <span className="fc-status-dot" style={{background:st.color}}/>
                        {f.status}
                      </span>
                    </td>
                    <td>
                      <div className="fc-actions">
                        <button className="fc-action-btn" title="Modifier">
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                          </svg>
                        </button>
                        <button className="fc-action-btn" title="Supprimer">
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2">
                            <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
                            <path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/>
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination" style={{marginTop:16}}>
            <button className="pag-btn" onClick={()=>setPage(p=>Math.max(1,p-1))} disabled={page===1}>← Previous</button>
            <span className="pag-info">Page {page} of {totalPages}</span>
            <button className="pag-btn" onClick={()=>setPage(p=>Math.min(totalPages,p+1))} disabled={page===totalPages}>Suivant →</button>
          </div>
        )}
      </div>
    </div>
  );
}
