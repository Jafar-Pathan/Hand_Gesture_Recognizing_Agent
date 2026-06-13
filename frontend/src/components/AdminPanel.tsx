/**
 * AdminPanel — admin controls for training and user management.
 *
 * Tabs:
 *   - Stats     — platform-wide KPI cards
 *   - Training  — trigger training, view job history
 *   - Users     — paginated user list with deactivation
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart2,
  Users,
  Cpu,
  Play,
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { adminApi, trainingApi, type StatsOut, type TrainStatusOut } from '../api/client';

type Tab = 'stats' | 'training' | 'users';

// ── Stats Tab ────────────────────────────────────────────────────────────────

function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: number | string; icon: React.ElementType; color: string;
}) {
  return (
    <div className={`bg-gray-700/30 rounded-xl p-4 border border-gray-600/20`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

function StatsTab() {
  const [stats, setStats] = useState<StatsOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    adminApi.stats()
      .then(({ data }) => setStats(data))
      .catch(() => setError('Failed to load statistics.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 text-blue-400 animate-spin" /></div>;
  if (error) return <p className="text-red-400 text-sm">{error}</p>;
  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      <StatCard label="Total Users" value={stats.total_users} icon={Users} color="text-blue-400" />
      <StatCard label="Active Users" value={stats.active_users} icon={Users} color="text-green-400" />
      <StatCard label="Total Predictions" value={stats.total_predictions} icon={BarChart2} color="text-purple-400" />
      <StatCard label="Predictions Today" value={stats.predictions_today} icon={BarChart2} color="text-yellow-400" />
      <StatCard label="Training Jobs" value={stats.total_training_jobs} icon={Cpu} color="text-teal-400" />
    </div>
  );
}

// ── Training Tab ─────────────────────────────────────────────────────────────

const STATUS_ICONS: Record<string, React.ReactNode> = {
  queued: <RefreshCw className="w-3.5 h-3.5 text-gray-400" />,
  running: <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin" />,
  done: <CheckCircle className="w-3.5 h-3.5 text-green-400" />,
  failed: <XCircle className="w-3.5 h-3.5 text-red-400" />,
};

const STATUS_COLORS: Record<string, string> = {
  queued: 'text-gray-400',
  running: 'text-blue-400',
  done: 'text-green-400',
  failed: 'text-red-400',
};

function TrainingTab() {
  const [backbone, setBackbone] = useState('cnn');
  const [epochs, setEpochs] = useState(50);
  const [batchSize, setBatchSize] = useState(32);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState('');
  const [jobs, setJobs] = useState<TrainStatusOut[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);

  const loadJobs = useCallback(() => {
    trainingApi.history()
      .then(({ data }) => setJobs(data.jobs ?? []))
      .catch(() => {})
      .finally(() => setJobsLoading(false));
  }, []);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  const handleStart = async () => {
    setStartError('');
    setIsStarting(true);
    try {
      await trainingApi.start(backbone, epochs, batchSize);
      loadJobs();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to start training.';
      setStartError(msg);
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Start training form */}
      <div className="bg-gray-700/30 rounded-xl p-4 border border-gray-600/20 space-y-3">
        <h3 className="text-sm font-semibold text-gray-200">Start New Training</h3>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-[11px] text-gray-400 block mb-1">Backbone</label>
            <select
              value={backbone}
              onChange={(e) => setBackbone(e.target.value)}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="cnn">Custom CNN</option>
              <option value="mobilenetv2">MobileNetV2</option>
              <option value="efficientnetb0">EfficientNetB0</option>
            </select>
          </div>
          <div>
            <label className="text-[11px] text-gray-400 block mb-1">Epochs</label>
            <input
              type="number"
              value={epochs}
              min={1}
              max={500}
              onChange={(e) => setEpochs(parseInt(e.target.value) || 50)}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="text-[11px] text-gray-400 block mb-1">Batch Size</label>
            <input
              type="number"
              value={batchSize}
              min={1}
              max={512}
              onChange={(e) => setBatchSize(parseInt(e.target.value) || 32)}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
        {startError && (
          <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            {startError}
          </div>
        )}
        <button
          onClick={handleStart}
          disabled={isStarting}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg px-4 py-2 text-xs font-medium text-white transition-all"
        >
          {isStarting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {isStarting ? 'Starting…' : 'Start Training'}
        </button>
      </div>

      {/* Job history */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-200">Job History</h3>
          <button onClick={loadJobs} className="text-[11px] text-gray-500 hover:text-gray-300 flex items-center gap-1 transition-colors">
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>
        {jobsLoading ? (
          <div className="flex justify-center py-4"><Loader2 className="w-4 h-4 text-gray-500 animate-spin" /></div>
        ) : jobs.length === 0 ? (
          <p className="text-gray-600 text-xs text-center py-4">No training jobs yet.</p>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
            {jobs.map((job) => (
              <div key={job.job_id} className="bg-gray-700/30 rounded-lg px-3 py-2.5 border border-gray-600/20 flex items-center gap-3 text-xs">
                {STATUS_ICONS[job.status]}
                <span className={`font-medium ${STATUS_COLORS[job.status]}`}>{job.status}</span>
                <span className="text-gray-400">{job.backbone}</span>
                <span className="text-gray-500">{job.epochs} epochs</span>
                {job.val_accuracy != null && (
                  <span className="text-green-400 ml-auto">val acc: {(job.val_accuracy * 100).toFixed(1)}%</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Users Tab ────────────────────────────────────────────────────────────────

function UsersTab() {
  const [users, setUsers] = useState<Array<{ id: number; username: string; email: string; is_admin: boolean; is_active: boolean; prediction_count: number }>>([]);
  const [loading, setLoading] = useState(true);

  const loadUsers = useCallback(() => {
    adminApi.users()
      .then(({ data }) => setUsers(data.users ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleDeactivate = async (userId: number) => {
    await adminApi.deactivateUser(userId);
    loadUsers();
  };

  if (loading) return <div className="flex justify-center py-6"><Loader2 className="w-4 h-4 text-gray-500 animate-spin" /></div>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-700/50">
            <th className="text-left text-gray-500 pb-2 pr-3">User</th>
            <th className="text-left text-gray-500 pb-2 pr-3">Email</th>
            <th className="text-right text-gray-500 pb-2 pr-3">Predictions</th>
            <th className="text-center text-gray-500 pb-2 pr-3">Role</th>
            <th className="text-center text-gray-500 pb-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="border-b border-gray-700/20 hover:bg-gray-700/20 transition-colors">
              <td className="py-2 pr-3 text-gray-300 font-medium">{user.username}</td>
              <td className="py-2 pr-3 text-gray-500">{user.email}</td>
              <td className="py-2 pr-3 text-gray-400 text-right font-mono">{user.prediction_count}</td>
              <td className="py-2 pr-3 text-center">
                <span className={`px-1.5 py-0.5 rounded text-[10px] ${user.is_admin ? 'bg-purple-500/20 text-purple-400' : 'bg-gray-600/30 text-gray-500'}`}>
                  {user.is_admin ? 'admin' : 'user'}
                </span>
              </td>
              <td className="py-2 text-center">
                {user.is_active ? (
                  <button
                    onClick={() => handleDeactivate(user.id)}
                    className="text-[10px] text-red-400 hover:text-red-300 transition-colors"
                  >
                    Deactivate
                  </button>
                ) : (
                  <span className="text-[10px] text-gray-600">Inactive</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main AdminPanel ──────────────────────────────────────────────────────────

export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState<Tab>('stats');

  const tabs: Array<{ id: Tab; label: string; icon: React.ElementType }> = [
    { id: 'stats', label: 'Stats', icon: BarChart2 },
    { id: 'training', label: 'Training', icon: Cpu },
    { id: 'users', label: 'Users', icon: Users },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold text-gray-200">Admin Panel</h2>
        <div className="flex bg-gray-700/40 rounded-lg p-0.5 gap-0.5">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === id
                  ? 'bg-gray-600 text-white'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'stats' && <StatsTab />}
      {activeTab === 'training' && <TrainingTab />}
      {activeTab === 'users' && <UsersTab />}
    </div>
  );
}
