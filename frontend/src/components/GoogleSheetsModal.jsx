import React, { useState } from 'react';
import { X, FileSpreadsheet, CheckCircle, AlertCircle, Loader2, ExternalLink, Database } from 'lucide-react';
import { api } from '../services/api';

export default function GoogleSheetsModal({ isOpen, onClose, selectedCount, onSyncSuccess }) {
  const [spreadsheetId, setSpreadsheetId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSync = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.syncToGoogleSheets({
        spreadsheet_id: spreadsheetId.trim() || undefined,
      });

      setResult(response);
      if (onSyncSuccess) {
        onSyncSuccess(response);
      }
    } catch (err) {
      setError(err.message || 'Sync failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Google Sheets Integration</h2>
              <p className="text-xs text-slate-400">Save and synchronize influencer records to Google Drive</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSync} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {result && (
            <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-200 text-xs space-y-2">
              <div className="flex items-center gap-2 font-semibold text-emerald-300 text-sm">
                <CheckCircle className="w-4 h-4" />
                <span>{result.message}</span>
              </div>
              <div className="text-slate-300 pt-1">
                Mode: <span className="font-semibold text-white">{result.mode}</span> | Records: <span className="font-semibold text-white">{result.synced_count}</span>
              </div>
            </div>
          )}

          <div className="p-3.5 rounded-xl bg-slate-800/50 border border-slate-700/60 text-xs text-slate-300 space-y-2">
            <div className="flex items-center gap-2 text-slate-200 font-semibold">
              <Database className="w-4 h-4 text-purple-400" />
              <span>Dual-Mode Synchronization Engine</span>
            </div>
            <p className="text-slate-400 leading-relaxed">
              When Google Cloud credentials are configured in <code className="text-purple-300">backend/google_credentials.json</code>, records push straight into your Google Drive spreadsheet.
            </p>
            <p className="text-slate-400 leading-relaxed">
              In demo mode, records seamlessly export to <code className="text-emerald-300">backend/app/data/google_sheets_synced_export.csv</code> and update sync flags automatically.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Google Spreadsheet ID (Optional)
            </label>
            <input
              type="text"
              value={spreadsheetId}
              onChange={(e) => setSpreadsheetId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              placeholder="e.g. 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              Leave blank to use default configuration or local synced storage.
            </p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold shadow-lg shadow-emerald-600/25 transition-all disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Syncing Records...</span>
                </>
              ) : (
                <>
                  <FileSpreadsheet className="w-4 h-4" />
                  <span>Sync to Sheets</span>
                </>
              )}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}

