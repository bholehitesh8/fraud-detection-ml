"""
Overhaul app/static/css/style.css to apply the complete Enterprise
Charcoal + Emerald + Teal + White Design System.
"""
import re

with open("app/static/css/style.css", "r", encoding="utf-8") as f:
    css = f.read()

# 1. Replace the root variables block
root_pattern = re.compile(r':root\s*\{[^}]*\}', re.DOTALL)
new_root = """:root {
  /* Surface & Base Palette - Enterprise Clean Light Theme */
  --bg-primary: #F8FAFC;
  --bg-secondary: #F1F5F9;
  --bg-surface: #FFFFFF;
  --bg-surface-elevated: #F8FAFC;
  --bg-surface-hover: #F1F5F9;
  --bg-glass: rgba(255, 255, 255, 0.9);
  --bg-glass-card: #FFFFFF;

  /* Primary Enterprise Neutrals */
  --color-primary-navy: #111827;
  --color-graphite: #1F2937;
  --color-slate: #374151;

  /* Accents (Zero Blue) */
  --color-emerald: #10B981;
  --color-emerald-dark: #059669;
  --color-teal: #14B8A6;
  --color-teal-dark: #0D9488;
  --accent-blue: #10B981;
  --accent-blue-hover: #059669;
  --accent-cyan: #14B8A6;
  --accent-purple: #8B5CF6;
  --accent-indigo: #6366F1;

  /* Borders & Focus */
  --border-subtle: #E2E8F0;
  --border-strong: #CBD5E1;
  --border-focus: #10B981;

  /* Typography */
  --text-primary: #111827;
  --text-secondary: #64748B;
  --text-muted: #94A3B8;
  --text-light: #475569;
  --text-on-dark: #F8FAFC;

  /* Risk & Status Indicators */
  --status-safe: #10B981;
  --status-safe-bg: rgba(16, 185, 129, 0.1);
  --status-safe-border: rgba(16, 185, 129, 0.25);

  --status-fraud: #EF4444;
  --status-fraud-bg: rgba(239, 68, 68, 0.1);
  --status-fraud-border: rgba(239, 68, 68, 0.25);

  --status-warn: #F59E0B;
  --status-warn-bg: rgba(245, 158, 11, 0.1);
  --status-warn-border: rgba(245, 158, 11, 0.25);

  --status-info: #14B8A6;
  --status-info-bg: rgba(20, 184, 166, 0.1);
  --status-info-border: rgba(20, 184, 166, 0.25);

  /* Shadows & Elevations */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
  --shadow-glow-blue: 0 0 16px rgba(16, 185, 129, 0.2);
  --shadow-glow-green: 0 0 16px rgba(16, 185, 129, 0.2);
  --shadow-glow-red: 0 0 16px rgba(239, 68, 68, 0.2);

  /* Geometry & Motion */
  --radius-xs: 4px;
  --radius-sm: 8px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 16px;
  --radius-btn: 8px;
  --radius-card: 14px;
  --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}"""

css = root_pattern.sub(new_root, css, count=1)

# 2. Specific replacements of blue hex values in CSS rules
replacements = [
    # General blue buttons & gradients
    ("background: linear-gradient(135deg, var(--accent-blue), var(--accent-blue-hover));", "background: linear-gradient(135deg, #10B981, #0D9488);"),
    ("box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);", "box-shadow: 0 1px 3px rgba(16, 185, 129, 0.25);"),
    ("box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6);", "box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);"),
    ("background: linear-gradient(135deg, var(--accent-blue), #1d4ed8);", "background: linear-gradient(135deg, #10B981, #14B8A6);"),
    ("background: linear-gradient(135deg, var(--accent-blue), #2563eb);", "background: linear-gradient(135deg, #10B981, #0D9488);"),
    ("box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);", "box-shadow: 0 1px 3px rgba(16, 185, 129, 0.2);"),
    ("box-shadow: 0 4px 14px rgba(59, 130, 246, 0.45);", "box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);"),
    ("border-color: rgba(59, 130, 246, 0.35);", "border-color: #CBD5E1;"),
    ("background: radial-gradient(circle, rgba(59, 130, 246, 0.12) 0%, rgba(9, 13, 22, 0) 70%);", "display: none;"),
    ("background: radial-gradient(circle, rgba(6, 182, 212, 0.08) 0%, rgba(9, 13, 22, 0) 70%);", "display: none;"),
    ("color: #60a5fa;", "color: #10B981;"),
    ("color: #38bdf8;", "color: #14B8A6;"),
    ("color: #06b6d4;", "color: #14B8A6;"),
    ("border-color: #38bdf8;", "border-color: #10B981;"),
    ("background: #38bdf8;", "background: #10B981;"),
    ("box-shadow: 0 0 8px #38bdf8;", "box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);"),
    ("background: linear-gradient(135deg, #2563eb, #06b6d4);", "background: linear-gradient(135deg, #10B981, #14B8A6);"),
    ("box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);", "box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);"),
    ("background: linear-gradient(135deg, #38bdf8, #818cf8);", "background: linear-gradient(135deg, #10B981, #14B8A6);"),
    ("background: linear-gradient(135deg, #4f46e5, #06b6d4);", "background: linear-gradient(135deg, #10B981, #14B8A6);"),
    ("background: linear-gradient(90deg, rgba(37, 99, 235, 0.18), rgba(6, 182, 212, 0.08));", "background: rgba(16, 185, 129, 0.12);"),
    ("border-color: rgba(59, 130, 246, 0.35);", "border-color: rgba(16, 185, 129, 0.25);"),
    ("box-shadow: inset 0 0 12px rgba(59, 130, 246, 0.1);", "box-shadow: none;"),
    (".kpi-card.kpi-blue::before { background: linear-gradient(90deg, #3b82f6, #06b6d4); }", ".kpi-card.kpi-blue::before { background: linear-gradient(90deg, #10B981, #14B8A6); }"),
    (".kpi-card.kpi-cyan::before { background: linear-gradient(90deg, #06b6d4, #3b82f6); }", ".kpi-card.kpi-cyan::before { background: linear-gradient(90deg, #14B8A6, #10B981); }"),
    ("background: linear-gradient(135deg, #2563eb, #0ea5e9) !important;", "background: linear-gradient(135deg, #10B981, #0D9488) !important;"),
    ("box-shadow: 0 4px 15px rgba(37, 99, 235, 0.35) !important;", "box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3) !important;"),
    ("box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5) !important;", "box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4) !important;"),
    ("background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%)", "background: linear-gradient(135deg, #10B981 0%, #0D9488 100%)"),
    ("box-shadow: 0 0 12px rgba(2, 132, 199, 0.4);", "box-shadow: 0 0 12px rgba(16, 185, 129, 0.35);"),
    (".node-input { background: #38bdf8; border-color: #0284c7; box-shadow: 0 0 10px rgba(56, 189, 248, 0.5); }", ".node-input { background: #10B981; border-color: #059669; box-shadow: 0 0 10px rgba(16, 185, 129, 0.4); }"),
    ("linear-gradient(90deg, transparent, #38bdf8, transparent)", "linear-gradient(90deg, transparent, #10B981, transparent)"),
    (".fic-stat-dot.dot-blue { background-color: #3b82f6; }", ".fic-stat-dot.dot-blue { background-color: #14B8A6; }"),
    ("background: #0284c7;", "background: #10B981;"),
    ("border-color: #0284c7;", "border-color: #10B981;"),
    ("color: #38bdf8 !important;", "color: #10B981 !important;"),
    ("color: #60a5fa !important;", "color: #10B981 !important;"),
]

for old, new in replacements:
    css = css.replace(old, new)

# 3. Add Master Enterprise Design System Overrides at the very bottom
# to guarantee that every card, panel, button, and table matches the
# Charcoal + Emerald + Teal + White enterprise specification perfectly.
enterprise_appendix = """

/* ==========================================================================
   ENTERPRISE DESIGN SYSTEM: CHARCOAL + EMERALD + TEAL + WHITE SPECIFICATION
   Guaranteed modern SaaS aesthetics across Dashboard, Analytics, Login,
   Prediction, History, Admin, and Audit views.
   ========================================================================== */

/* 1. Global Page Background & Canvas */
body {
  background-color: #F8FAFC !important;
  color: #111827 !important;
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

body.dashboard-theme {
  background-color: #F8FAFC !important;
  color: #111827 !important;
}

body::before, body::after,
body.dashboard-theme::before, body.dashboard-theme::after {
  display: none !important;
}

/* 2. Premium Graphite Sidebar */
.app-sidebar {
  background-color: #111827 !important;
  border-right: 1px solid #1F2937 !important;
  box-shadow: 1px 0 3px rgba(0, 0, 0, 0.05) !important;
}

.sidebar-header {
  border-bottom: 1px solid #1F2937 !important;
}

.brand-logo-badge {
  background: linear-gradient(135deg, #10B981, #0D9488) !important;
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3) !important;
}

.brand-name {
  color: #F8FAFC !important;
}

.brand-name-accent {
  color: #10B981 !important;
  background: none !important;
  -webkit-text-fill-color: #10B981 !important;
}

.sidebar-status-box {
  background: #1F2937 !important;
  border: 1px solid #374151 !important;
  border-radius: 8px !important;
}

.status-box-header {
  color: #10B981 !important;
}

.status-box-sub {
  color: #94A3B8 !important;
}

.nav-section-label {
  color: #64748B !important;
}

.sidebar-nav-item {
  color: #94A3B8 !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
}

.sidebar-nav-item:hover {
  color: #F8FAFC !important;
  background: rgba(255, 255, 255, 0.05) !important;
  border-color: transparent !important;
  transform: translateX(2px) !important;
}

.sidebar-nav-item.active {
  color: #10B981 !important;
  background: rgba(16, 185, 129, 0.12) !important;
  border: 1px solid rgba(16, 185, 129, 0.25) !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}

.sidebar-nav-item.active .nav-item-icon {
  color: #10B981 !important;
}

.sidebar-nav-item.active::before {
  background: #10B981 !important;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5) !important;
}

.sidebar-user-footer {
  background: #111827 !important;
  border-top: 1px solid #1F2937 !important;
}

.sidebar-user-card {
  background: #1F2937 !important;
  border: 1px solid #374151 !important;
  border-radius: 8px !important;
}

.user-avatar-badge {
  background: linear-gradient(135deg, #10B981, #0D9488) !important;
}

.user-profile-name {
  color: #F8FAFC !important;
}

.user-profile-role {
  color: #94A3B8 !important;
}

/* 3. Enterprise Buttons (8-10px radius, zero blue) */
.btn, .btn-primary, .btn-secondary, .btn-danger, .fic-evaluate-btn, .fic-refresh-btn, .ai-login-btn {
  border-radius: 8px !important;
  font-weight: 600 !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.btn-primary, .fic-evaluate-btn, .ai-login-btn {
  background: linear-gradient(135deg, #10B981 0%, #0D9488 100%) !important;
  color: #FFFFFF !important;
  border: 1px solid #059669 !important;
  box-shadow: 0 1px 2px rgba(16, 185, 129, 0.2) !important;
}

.btn-primary:hover, .fic-evaluate-btn:hover, .ai-login-btn:hover {
  background: linear-gradient(135deg, #059669 0%, #0F766E 100%) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
}

.btn-primary:active, .fic-evaluate-btn:active, .ai-login-btn:active {
  transform: translateY(0) !important;
}

.btn-primary:disabled, .btn:disabled {
  opacity: 0.6 !important;
  cursor: not-allowed !important;
  transform: none !important;
}

.btn-secondary, .fic-refresh-btn, .btn-period {
  background: #FFFFFF !important;
  color: #1F2937 !important;
  border: 1px solid #D1D5DB !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}

.btn-secondary:hover, .fic-refresh-btn:hover {
  background: #F3F4F6 !important;
  border-color: #9CA3AF !important;
  color: #111827 !important;
  transform: translateY(-1px) !important;
}

.btn-danger {
  background: #EF4444 !important;
  color: #FFFFFF !important;
  border: 1px solid #DC2626 !important;
}

.btn-danger:hover {
  background: #DC2626 !important;
}

/* 4. Enterprise Cards & Light Surfaces */
.card,
.fic-panel,
.fic-kpi-card,
.fic-health-panel,
.model-spec-card,
.table-container {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 14px !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.04) !important;
}

.card:hover, .fic-kpi-card:hover, .fic-panel:hover {
  border-color: #CBD5E1 !important;
}

/* Headings and Typography */
h1, h2, h3, h4, h5, h6,
.card-title,
.fic-panel-title,
.fic-card-name,
.stat-value {
  color: #111827 !important;
}

p, .card-subtitle, .fic-panel-sub, .fic-card-detail, .stat-label {
  color: #64748B !important;
}

/* 5. Dashboard Header Card (Navy-Charcoal) */
.fic-header-card {
  background: #111827 !important;
  border: 1px solid #1F2937 !important;
  border-radius: 14px !important;
  box-shadow: 0 4px 16px -2px rgba(17, 24, 39, 0.15) !important;
}

.fic-header-card .fic-title {
  color: #F8FAFC !important;
}

.fic-header-card .fic-subtitle {
  color: #94A3B8 !important;
}

.fic-emblem {
  background: linear-gradient(135deg, #10B981, #0D9488) !important;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.35) !important;
}

.fic-platform-badge {
  background: rgba(16, 185, 129, 0.15) !important;
  color: #10B981 !important;
  border: 1px solid rgba(16, 185, 129, 0.3) !important;
}

/* 6. KPI Cards */
.fic-kpi-card {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 14px !important;
  padding: 1.25rem !important;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease !important;
}

.fic-kpi-card:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 20px -4px rgba(15, 23, 42, 0.08) !important;
  border-color: #CBD5E1 !important;
}

.fic-kpi-label {
  color: #64748B !important;
  font-size: 0.76rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
}

.fic-kpi-val {
  color: #111827 !important;
  font-size: 1.85rem !important;
  font-weight: 800 !important;
}

.fic-kpi-desc {
  color: #94A3B8 !important;
}

/* 7. System Security Health Panel */
.fic-health-panel {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
}

.fic-health-header {
  border-bottom: 1px solid #F1F5F9 !important;
}

.fic-section-title {
  color: #475569 !important;
}

.fic-health-card {
  background: #F8FAFC !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 10px !important;
}

.fic-health-card:hover {
  border-color: #CBD5E1 !important;
  background: #F1F5F9 !important;
}

.fic-card-foot {
  color: #64748B !important;
}

.fic-card-foot strong {
  color: #111827 !important;
}

/* 8. Filters & Controls */
.fic-filter-bar {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 10px !important;
}

.fic-filter-title {
  color: #475569 !important;
}

.fic-select {
  background: #FFFFFF !important;
  border: 1px solid #D1D5DB !important;
  border-radius: 8px !important;
  color: #111827 !important;
}

.fic-select:focus {
  border-color: #10B981 !important;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.15) !important;
}

.fic-timeline-switch {
  background: #F1F5F9 !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 8px !important;
}

.fic-timeline-switch .btn-period {
  background: transparent !important;
  color: #64748B !important;
  border: none !important;
  box-shadow: none !important;
}

.fic-timeline-switch .btn-period:hover {
  color: #111827 !important;
}

.fic-timeline-switch .btn-period.active {
  background: #10B981 !important;
  color: #FFFFFF !important;
  box-shadow: 0 1px 3px rgba(16, 185, 129, 0.3) !important;
}

/* 9. Data Tables & Recent Activity */
.fic-data-table, .data-table {
  width: 100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
}

.fic-data-table thead th, .data-table thead th {
  background: #F8FAFC !important;
  color: #475569 !important;
  font-size: 0.74rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
  padding: 0.75rem 1rem !important;
  border-bottom: 1px solid #E2E8F0 !important;
}

.fic-data-table tbody td, .data-table tbody td {
  padding: 0.85rem 1rem !important;
  color: #111827 !important;
  font-size: 0.85rem !important;
  border-bottom: 1px solid #F1F5F9 !important;
  background: #FFFFFF !important;
}

.fic-data-table tbody tr:hover td, .data-table tbody tr:hover td {
  background: #F8FAFC !important;
}

.fic-table-search-input {
  background: #FFFFFF !important;
  border: 1px solid #D1D5DB !important;
  border-radius: 8px !important;
  color: #111827 !important;
}

.fic-table-search-input:focus {
  border-color: #10B981 !important;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.15) !important;
}

/* 10. AI Model Card & Subcomponents */
.fic-model-specs, .fic-metric-cell, .fic-insight-row, .fic-alert-item, .fic-donut-summary {
  background: #F8FAFC !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 8px !important;
}

.fic-spec-label, .fic-metric-name {
  color: #64748B !important;
}

.fic-spec-val, .fic-metric-num {
  color: #111827 !important;
}

.fic-insight-text {
  color: #374151 !important;
}

.fic-alert-amount strong {
  color: #111827 !important;
}

.fic-alert-time {
  color: #94A3B8 !important;
}

.fic-quick-actions-bar {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 10px !important;
}

.fic-quick-title {
  color: #64748B !important;
}

/* 11. Modal Dialogs */
.modal-card, .dashboard-theme .modal-card {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 14px !important;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
}

.modal-header, .dashboard-theme .modal-header {
  border-bottom: 1px solid #E2E8F0 !important;
}

.modal-header h3, .dashboard-theme .modal-header h3 {
  color: #111827 !important;
}

.modal-close, .dashboard-theme .modal-close {
  color: #64748B !important;
}

.modal-close:hover, .dashboard-theme .modal-close:hover {
  color: #111827 !important;
}

.detail-item, .dashboard-theme .detail-item {
  background: #F8FAFC !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 8px !important;
}

.detail-label, .dashboard-theme .detail-label {
  color: #64748B !important;
}

.detail-val, .dashboard-theme .detail-val {
  color: #111827 !important;
}

/* 12. Badges & Indicators */
.badge-safe, .fic-badge-tag.badge-emerald, .fic-status-chip.status-nominal {
  background: rgba(16, 185, 129, 0.1) !important;
  color: #059669 !important;
  border: 1px solid rgba(16, 185, 129, 0.25) !important;
}

.badge-fraud, .fic-alert-chip.has-alerts, .fic-severity-tag.tag-critical {
  background: rgba(239, 68, 68, 0.1) !important;
  color: #DC2626 !important;
  border: 1px solid rgba(239, 68, 68, 0.25) !important;
}

.badge-warning, .fic-status-chip.status-warning, .fic-severity-tag.tag-high {
  background: rgba(245, 158, 11, 0.1) !important;
  color: #D97706 !important;
  border: 1px solid rgba(245, 158, 11, 0.25) !important;
}

.badge-info, .fic-badge-tag.badge-cyan {
  background: rgba(20, 184, 166, 0.1) !important;
  color: #0D9488 !important;
  border: 1px solid rgba(20, 184, 166, 0.25) !important;
}

/* 13. Login Page Enterprise Split Theme */
.ai-login-wrapper {
  background: #111827 !important;
  border: 1px solid #1F2937 !important;
  border-radius: 16px !important;
  overflow: hidden !important;
  box-shadow: 0 25px 50px -12px rgba(17, 24, 39, 0.25) !important;
}

.ai-branding-pane {
  background: #111827 !important;
}

.ai-shield-emblem {
  background: rgba(16, 185, 129, 0.15) !important;
  border: 1px solid rgba(16, 185, 129, 0.35) !important;
  color: #10B981 !important;
  box-shadow: 0 0 16px rgba(16, 185, 129, 0.2) !important;
}

.ai-accent {
  color: #10B981 !important;
  text-shadow: none !important;
}

.ai-status-pulse {
  background: #10B981 !important;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5) !important;
}

.ai-login-card {
  background: #FFFFFF !important;
  border-left: 1px solid #E2E8F0 !important;
}

.ai-login-card .card-title {
  color: #111827 !important;
}

.ai-login-card .card-subtitle {
  color: #64748B !important;
}

.ai-login-card .field-label, .ai-login-card label {
  color: #374151 !important;
  font-weight: 600 !important;
}

.ai-login-card .form-control {
  background: #FFFFFF !important;
  border: 1px solid #D1D5DB !important;
  color: #111827 !important;
  border-radius: 8px !important;
}

.ai-login-card .form-control:focus {
  border-color: #10B981 !important;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15) !important;
}

.card-icon-bubble {
  background: rgba(16, 185, 129, 0.1) !important;
  border: 1px solid rgba(16, 185, 129, 0.25) !important;
  color: #10B981 !important;
}

.btn-demo-fill {
  background: #F8FAFC !important;
  border: 1px solid #E2E8F0 !important;
  color: #374151 !important;
  border-radius: 6px !important;
}

.btn-demo-fill:hover {
  background: #F1F5F9 !important;
  border-color: #CBD5E1 !important;
  color: #111827 !important;
}

/* 14. Responsive Layout Safety */
html, body {
  overflow-x: hidden !important;
  max-width: 100vw !important;
}
"""

css += enterprise_appendix

with open("app/static/css/style.css", "w", encoding="utf-8") as f:
    f.write(css)

print("Successfully updated app/static/css/style.css with the Enterprise Design System!")
