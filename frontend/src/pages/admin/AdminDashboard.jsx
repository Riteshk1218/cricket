import { Activity, CalendarCheck, Eye, Radio, Shield, Smartphone, Trophy, UserCheck, Users, Wifi } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ErrorBox, PageHeader, Spinner, Stat } from '../../components/ui'
import { useApi } from '../../lib/useApi'

const PIE = ['#22997b', '#3b82f6', '#a855f7']

export default function AdminDashboard() {
  const { data, loading, error, reload } = useApi('/analytics/dashboard/')
  useEffect(() => {
    const id = setInterval(reload, 15000)
    return () => clearInterval(id)
  }, [reload])
  if (loading && !data) return <Spinner />
  if (error) return <ErrorBox onRetry={reload}>{error}</ErrorBox>
  const { totals, realtime, traffic, android, popular_matches: popular, definitions } = data
  const clients = Object.entries(traffic.by_client).map(([name, value]) => ({ name, value }))
  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Refreshes every 15 seconds" icon={Activity} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {totals.users !== null && <Stat label="Registered users" value={totals.users} icon={Users} />}
        <Stat label="Tournaments" value={totals.tournaments} icon={Trophy} tone="amber" />
        <Stat label="Teams" value={totals.teams} icon={Shield} tone="sky" />
        <Stat label="Players" value={totals.players} icon={Users} tone="violet" />
        <Stat label="Matches" value={totals.matches} icon={CalendarCheck} />
        <Stat label="Live matches" value={totals.live_matches} icon={Radio} tone="red" />
        <Stat label="Completed matches" value={totals.completed_matches} icon={CalendarCheck} tone="sky" />
        <Stat label="Upcoming matches" value={totals.upcoming_matches} icon={CalendarCheck} tone="amber" />
        <Stat label="Active scorers (30 min)" value={totals.active_scorers} icon={UserCheck} tone="violet" />
        <Stat label="Connected viewers now" value={realtime.current_connections} icon={Wifi} tone="red" />
      </div>

      <h2 className="mb-3 mt-8 text-lg font-bold">Traffic</h2>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Page views today" value={traffic.page_views_today} icon={Eye} />
        <Stat label="Unique visitors today" value={traffic.unique_visitors_today} icon={Users} tone="sky" />
        <Stat label="Total match views" value={traffic.match_views_total} icon={Eye} tone="amber" />
        <Stat label="Total page views" value={traffic.page_views_total} icon={Eye} tone="violet" />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <div className="card p-4 xl:col-span-2">
          <h3 className="label">Daily visits (last 30 days)</h3>
          <div className="h-64">
            <ResponsiveContainer>
              <AreaChart data={traffic.daily}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="date" fontSize={11} tickFormatter={(d) => d.slice(5)} />
                <YAxis fontSize={11} allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="page_views" name="Page views" stroke="#22997b" fill="#22997b" fillOpacity={0.25} />
                <Area type="monotone" dataKey="unique_visitors" name="Unique visitors" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card p-4">
          <h3 className="label">Views by client</h3>
          <div className="h-64">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={clients} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} label>
                  {clients.map((c, i) => <Cell key={c.name} fill={PIE[i % PIE.length]} />)}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card p-4 xl:col-span-2">
          <h3 className="label">Monthly page views</h3>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={traffic.monthly}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="month" fontSize={11} />
                <YAxis fontSize={11} allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="page_views" name="Page views" fill="#22997b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="visitor_days" name="Visitor-days" fill="#f2b01e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card p-4">
          <h3 className="label flex items-center gap-2"><Smartphone className="h-4 w-4" /> Android app activity</h3>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div><dt className="text-xs text-slate-500">Screen views today</dt><dd className="text-xl font-bold">{android.screen_views_today}</dd></div>
            <div><dt className="text-xs text-slate-500">Devices today</dt><dd className="text-xl font-bold">{android.unique_devices_today}</dd></div>
            <div><dt className="text-xs text-slate-500">Screen views (30 days)</dt><dd className="text-xl font-bold">{android.screen_views_30d}</dd></div>
            <div><dt className="text-xs text-slate-500">Live connections</dt><dd className="text-xl font-bold">{android.live_connections}</dd></div>
          </dl>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <h3 className="label">Viewers per live match (right now)</h3>
          <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
            {realtime.viewers_per_match.map((r) => (
              <li key={r.match} className="flex justify-between py-2"><Link className="hover:underline" to={`/matches/${r.match}`}>{r.title}</Link><b>{r.viewers}</b></li>
            ))}
            {!realtime.viewers_per_match.length && <li className="py-2 text-slate-500">Nobody is watching a match right now.</li>}
          </ul>
        </div>
        <div className="card p-4">
          <h3 className="label">Popular matches (all-time views)</h3>
          <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
            {popular.map((r) => (
              <li key={r.match} className="flex justify-between gap-2 py-2"><Link className="truncate hover:underline" to={`/matches/${r.match}`}>{r.title} <span className="text-xs text-slate-500">{r.tournament}</span></Link><b>{r.views}</b></li>
            ))}
            {!popular.length && <li className="py-2 text-slate-500">No match views recorded yet.</li>}
          </ul>
        </div>
      </div>
      <div className="mt-4 rounded-xl bg-slate-100 p-4 text-xs text-slate-600 dark:bg-slate-900 dark:text-slate-400">
        <p className="mb-1 font-semibold">How these numbers differ</p>
        <ul className="list-disc space-y-0.5 pl-4">
          {Object.entries(definitions).map(([k, v]) => <li key={k}><b>{k.replace(/_/g, ' ')}:</b> {v}</li>)}
        </ul>
      </div>
    </div>
  )
}
