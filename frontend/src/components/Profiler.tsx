import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import { Activity, AlertTriangle, Layers, Clock } from 'lucide-react';

export default function Profiler() {
  // Mock data for the Profiler
  const [metrics] = useState({
    cpi: 1.24,
    totalCycles: 15420,
    totalInstructions: 12435,
    frequency: '1.2 GHz',
  });

  const hazardData = [
    { name: 'Data Hazards', value: 400 },
    { name: 'Control Hazards', value: 150 },
  ];
  const COLORS = ['#06B6D4', '#EF4444']; // Cyan and Red

  const cacheData = [
    { cycle: 1000, hitRate: 85, missRate: 15 },
    { cycle: 2000, hitRate: 88, missRate: 12 },
    { cycle: 3000, hitRate: 82, missRate: 18 },
    { cycle: 4000, hitRate: 90, missRate: 10 },
    { cycle: 5000, hitRate: 92, missRate: 8 },
    { cycle: 6000, hitRate: 95, missRate: 5 },
  ];

  return (
    <div className="container overflow-y-auto h-full p-6 text-slate-200">
      <h2 className="text-2xl font-bold mb-6 text-white flex items-center gap-2">
        <Activity className="text-accent-cyan" />
        Performance Profiler
      </h2>

      {/* KPI Blocks */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow-sm flex flex-col justify-center">
          <div className="text-slate-400 text-sm mb-1 flex items-center gap-2"><Clock size={16} /> Overall CPI</div>
          <div className="text-3xl font-mono text-white">{metrics.cpi.toFixed(2)}</div>
        </div>
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow-sm flex flex-col justify-center">
          <div className="text-slate-400 text-sm mb-1">Total Cycles</div>
          <div className="text-3xl font-mono text-emerald-400">{metrics.totalCycles.toLocaleString()}</div>
        </div>
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow-sm flex flex-col justify-center">
          <div className="text-slate-400 text-sm mb-1">Total Instructions</div>
          <div className="text-3xl font-mono text-cyan-400">{metrics.totalInstructions.toLocaleString()}</div>
        </div>
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow-sm flex flex-col justify-center">
          <div className="text-slate-400 text-sm mb-1">Frequency</div>
          <div className="text-3xl font-mono text-indigo-400">{metrics.frequency}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Hazard Breakdown Chart */}
        <div className="bg-slate-800 p-5 rounded-lg border border-slate-700">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber-500" />
            Hazard Breakdown (Stalls)
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={hazardData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  fill="#8884d8"
                  paddingAngle={5}
                  dataKey="value"
                  label
                >
                  {hazardData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', color: '#fff' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Cache Hit Rate Chart */}
        <div className="bg-slate-800 p-5 rounded-lg border border-slate-700">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Layers size={18} className="text-indigo-400" />
            Cache Efficacy over Time
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={cacheData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="cycle" stroke="#94A3B8" fontSize={12} />
                <YAxis stroke="#94A3B8" fontSize={12} />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', color: '#fff' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Legend />
                <Line type="monotone" dataKey="hitRate" name="Hit Rate %" stroke="#10B981" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="missRate" name="Miss Rate %" stroke="#EF4444" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
