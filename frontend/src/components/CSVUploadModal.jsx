import React, { useState } from 'react';
import { X, Upload, FileText, CheckCircle, AlertCircle, Download, Loader2 } from 'lucide-react';
import { api } from '../services/api';

export default function CSVUploadModal({ isOpen, onClose, onUploadComplete }) {
  const [file, setFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please choose a CSV file first.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.uploadCSV(file);
      setResult(response);
      if (onUploadComplete) {
        onUploadComplete(response);
      }
    } catch (err) {
      setError(err.message || 'CSV upload failed.');
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
            <div className="p-2 rounded-lg bg-slate-800 text-purple-400 border border-slate-700">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Import Influencer CSV</h2>
              <p className="text-xs text-slate-400">Batch upload creator records with automatic deduplication</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleUpload} className="p-6 space-y-4">
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
                <span>Upload & Deduplication Summary</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center pt-2">
                <div className="bg-slate-900/60 p-2 rounded-lg">
                  <div className="text-base font-bold text-white">{result.rows_detected}</div>
                  <div className="text-[10px] text-slate-400">Rows Detected</div>
                </div>
                <div className="bg-slate-900/60 p-2 rounded-lg">
                  <div className="text-base font-bold text-emerald-400">{result.imported}</div>
                  <div className="text-[10px] text-slate-400">Imported</div>
                </div>
                <div className="bg-slate-900/60 p-2 rounded-lg">
                  <div className="text-base font-bold text-amber-400">{result.duplicates_skipped}</div>
                  <div className="text-[10px] text-slate-400">Duplicates Filtered</div>
                </div>
              </div>
            </div>
          )}

          {/* File Drop Area */}
          <div className="border-2 border-dashed border-slate-700 hover:border-purple-500/80 rounded-xl p-6 text-center cursor-pointer transition-colors bg-slate-800/30">
            <input
              type="file"
              accept=".csv,.txt"
              onChange={handleFileChange}
              className="hidden"
              id="csv-file-input"
            />
            <label htmlFor="csv-file-input" className="cursor-pointer block">
              <FileText className="w-10 h-10 text-slate-400 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-200">
                {file ? file.name : 'Click to browse or drop CSV file here'}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Accepted columns: name, username, profile_url, niche, followers, email, location
              </p>
            </label>
          </div>

          {/* Template Download */}
          <div className="flex items-center justify-between text-xs p-3 rounded-lg bg-slate-800/60 border border-slate-700/60">
            <span className="text-slate-400">Need a pre-formatted template?</span>
            <a
              href="/api/v1/discovery/sample-csv"
              download="sample_influencers_template.csv"
              className="flex items-center gap-1.5 text-purple-400 hover:text-purple-300 font-medium"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Sample CSV</span>
            </a>
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={isLoading || !file}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-semibold shadow-lg shadow-purple-600/30 transition-all disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing CSV...</span>
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  <span>Import Records</span>
                </>
              )}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}

