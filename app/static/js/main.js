/**
 * Fraud Detection in Online Transactions - Client-Side Controller
 * Modern Interactive AJAX Prediction, Live Filters, Health Monitor, and Detail Modal
 */

// Global Helpers (Accessible from inline HTML event attributes)
window.copyText = function(text, btnElement) {
    if (!navigator.clipboard) {
        // Fallback for older browsers or non-HTTPS
        const textarea = document.createElement("textarea");
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
    } else {
        navigator.clipboard.writeText(text);
    }
    
    if (btnElement) {
        const originalText = btnElement.innerHTML;
        btnElement.innerHTML = "✓ Copied!";
        btnElement.style.color = "var(--status-safe)";
        setTimeout(() => {
            btnElement.innerHTML = originalText;
            btnElement.style.color = "";
        }, 1500);
    }
    window.showToast("Reference copied to clipboard: " + text, "success");
};

window.showToast = function(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast-msg ${type}`;
    const icon = type === "success" ? "✓" : (type === "error" ? "⚠️" : "ℹ️");
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
};

window.inspectTransaction = function(identifier) {
    const modal = document.getElementById("detailModal");
    const modalBody = document.getElementById("modalBody");
    const modalTitle = document.getElementById("modalTitle");
    if (!modal || !modalBody) return;

    modal.classList.add("active");
    modalBody.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 2rem;">
            <div class="spinner" style="margin-right: 0.5rem;"></div> Loading transaction details for <strong>${identifier}</strong>...
        </div>
    `;

    fetch(`/api/predictions/${encodeURIComponent(identifier)}`)
        .then(res => {
            if (!res.ok) throw new Error("Record not found or error loading.");
            return res.json();
        })
        .then(data => {
            if (!data.success || !data.prediction) {
                modalBody.innerHTML = `<div style="grid-column: 1 / -1; color: var(--status-fraud); text-align: center;">Record not found.</div>`;
                return;
            }
            const p = data.prediction;
            modalTitle.innerText = `Audit Record: ${p.transaction_ref}`;

            const isFraud = p.is_fraud;
            const statusColor = isFraud ? "var(--status-fraud)" : "var(--status-safe)";
            const statusLabel = isFraud ? "FRAUDULENT" : "LEGITIMATE";

            modalBody.innerHTML = `
                <div class="detail-item" style="grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div class="detail-label">Decision & Risk Status</div>
                        <div class="detail-val" style="color: ${statusColor}; font-size: 1.15rem;">
                            ${statusLabel} &bull; Tier: ${p.risk_level}
                        </div>
                    </div>
                    <span class="badge ${isFraud ? 'badge-fraud' : 'badge-safe'}">${p.prediction_label}</span>
                </div>

                <div class="detail-item">
                    <div class="detail-label">Transaction Reference</div>
                    <div class="detail-val"><code>${p.transaction_ref}</code></div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Transaction Type</div>
                    <div class="detail-val"><strong>${p.transaction_type}</strong></div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">Submitted Amount</div>
                    <div class="detail-val">${Number(p.amount).toFixed(2)} ${p.currency || 'USD'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Normalized Amount (USD)</div>
                    <div class="detail-val">$${Number(p.normalized_amount || p.amount).toFixed(2)} (Rate: ${p.exchange_rate || 1.0})</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">Fraud Probability</div>
                    <div class="detail-val" style="color: ${statusColor};">${(Number(p.fraud_probability || 0) * 100).toFixed(2)}%</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Model Confidence</div>
                    <div class="detail-val">${Number(p.confidence_score || 0).toFixed(2)}%</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">Sender Balances</div>
                    <div class="detail-val">Old: $${Number(p.old_balance_org || 0).toFixed(2)} &rarr; New: $${Number(p.new_balance_orig || 0).toFixed(2)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Receiver Balances</div>
                    <div class="detail-val">Old: $${Number(p.old_balance_dest || 0).toFixed(2)} &rarr; New: $${Number(p.new_balance_dest || 0).toFixed(2)}</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">Origin Account (Masked)</div>
                    <div class="detail-val">${p.sender_account || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Destination Account (Masked)</div>
                    <div class="detail-val">${p.receiver_account || 'N/A'}</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">Routing & Channel</div>
                    <div class="detail-val">${p.device_type || 'Web'} &bull; ${p.location || 'Domestic'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Hour Step</div>
                    <div class="detail-val">Step ${p.step || 1}</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">Inference Model Engine</div>
                    <div class="detail-val">${p.model_name || 'ExtraTrees'} (v${p.model_version || '1.0.0'})</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Logged Audit Timestamp</div>
                    <div class="detail-val">${p.created_at || 'Recently recorded'}</div>
                </div>
            `;
        })
        .catch(err => {
            modalBody.innerHTML = `<div style="grid-column: 1 / -1; color: var(--status-fraud); text-align: center;">Error loading record: ${err.message}</div>`;
        });
};

window.resetPredictionWorkspace = function() {
    const form = document.getElementById("predictionForm");
    if (form) form.reset();
    const outcome = document.getElementById("ajaxOutcomeContainer");
    if (outcome) outcome.innerHTML = "";
    const serverCard = document.getElementById("serverOutcomeCard");
    if (serverCard) serverCard.style.display = "none";
    const preCard = document.getElementById("preAnalysisCard");
    if (preCard) preCard.style.display = "block";
    const loadingCard = document.getElementById("predictLoadingCard");
    if (loadingCard) loadingCard.style.display = "none";
    window.showToast("Workspace reset for next transaction evaluation.", "info");
};

// DOM Content Loaded Handler
document.addEventListener("DOMContentLoaded", () => {
    // 0. Dynamic Time-Based Greeting & Current Date
    const greetingEl = document.getElementById("dynamicGreetingWord");
    if (greetingEl) {
        const curHour = new Date().getHours();
        let word = "Good evening";
        if (curHour >= 5 && curHour < 12) {
            word = "Good morning";
        } else if (curHour >= 12 && curHour < 17) {
            word = "Good afternoon";
        }
        greetingEl.innerText = word;
    }

    const dateEl = document.getElementById("topbarDateStr");
    if (dateEl) {
        const now = new Date();
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        dateEl.innerText = now.toLocaleDateString('en-US', options);
    }

    // 0b. Enterprise Mobile Sidebar Drawer Controller
    const sidebar = document.getElementById("appSidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarCloseBtn = document.getElementById("sidebarCloseBtn");
    const sidebarBackdrop = document.getElementById("sidebarBackdrop");

    function openSidebar() {
        if (sidebar) sidebar.classList.add("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.add("active");
        document.body.style.overflow = "hidden";
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.remove("active");
        document.body.style.overflow = "";
    }

    if (sidebarToggle) sidebarToggle.addEventListener("click", openSidebar);
    if (sidebarCloseBtn) sidebarCloseBtn.addEventListener("click", closeSidebar);
    if (sidebarBackdrop) sidebarBackdrop.addEventListener("click", closeSidebar);

    // 1. Legacy Mobile Navigation Toggle & Outside Click Handler
    const navToggle = document.getElementById("navToggle");
    const navMenuWrapper = document.getElementById("navMenuWrapper");
    const navLinks = document.getElementById("navLinks");
    if (navToggle) {
        navToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            const isOpen = navMenuWrapper ? navMenuWrapper.classList.toggle("open") : (navLinks ? navLinks.classList.toggle("open") : false);
            navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });
        document.addEventListener("click", (e) => {
            if (navMenuWrapper && navMenuWrapper.classList.contains("open") && !navMenuWrapper.contains(e.target) && !navToggle.contains(e.target)) {
                navMenuWrapper.classList.remove("open");
                navToggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    // Auto-scroll to tab anchor if present in URL
    if (window.location.hash) {
        const targetSection = document.querySelector(window.location.hash);
        if (targetSection) {
            setTimeout(() => {
                targetSection.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 150);
        }
    }

    // 2. System Health Status Poll
    const statusText = document.getElementById("statusText");
    const statusDot = document.getElementById("statusDot");
    fetch("/api/health")
        .then(res => res.json())
        .then(data => {
            if (data.status === "healthy" && data.ml_model_loaded) {
                if (statusText) statusText.innerText = `${data.model_details?.name || 'ExtraTrees'} Active`;
                if (statusDot) statusDot.className = "status-dot";

                // Update about page diagnostics if present
                const diagModel = document.getElementById("diagModel");
                const diagPrep = document.getElementById("diagPrep");
                const diagDb = document.getElementById("diagDb");
                if (diagModel) diagModel.innerText = `${data.model_details?.name || 'ExtraTrees'} v${data.model_details?.version || '1.0'}`;
                if (diagPrep) diagPrep.innerText = `Loaded (${data.model_details?.engineered_feature_count || 16} Feats)`;
                if (diagDb) diagDb.innerText = data.database === "connected" ? "Connected (SQLite)" : "Degraded";
            } else {
                if (statusText) statusText.innerText = "System Degraded";
                if (statusDot) statusDot.className = "status-dot degraded";
            }
        })
        .catch(() => {
            if (statusText) statusText.innerText = "Service Offline";
            if (statusDot) statusDot.className = "status-dot degraded";
        });

    // 3. Modal Close Listeners
    const modal = document.getElementById("detailModal");
    const modalClose = document.getElementById("modalClose");
    if (modalClose && modal) {
        modalClose.addEventListener("click", () => modal.classList.remove("active"));
        modal.addEventListener("click", (e) => {
            if (e.target === modal) modal.classList.remove("active");
        });
    }
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal && modal.classList.contains("active")) {
            modal.classList.remove("active");
        }
    });

    // 4. Test Scenario Demo Presets
    const presets = {
        safe: {
            amount: "45.00",
            currency: "USD",
            transaction_type: "PAYMENT",
            old_balance_org: "1200.00",
            new_balance_orig: "1155.00",
            old_balance_dest: "500.00",
            new_balance_dest: "545.00",
            step: "1",
            sender_account: "AC-98765432",
            receiver_account: "MC-11223344",
            device_type: "Mobile",
            location: "Domestic"
        },
        drain: {
            amount: "50000.00",
            currency: "USD",
            transaction_type: "TRANSFER",
            old_balance_org: "50000.00",
            new_balance_orig: "0.00",
            old_balance_dest: "0.00",
            new_balance_dest: "50000.00",
            step: "1",
            sender_account: "AC-55443322",
            receiver_account: "AC-99001122",
            device_type: "Web",
            location: "International"
        },
        cashout: {
            amount: "18500.00",
            currency: "USD",
            transaction_type: "CASH_OUT",
            old_balance_org: "19000.00",
            new_balance_orig: "500.00",
            old_balance_dest: "0.00",
            new_balance_dest: "0.00",
            step: "1",
            sender_account: "AC-12345678",
            receiver_account: "ATM-887766",
            device_type: "POS",
            location: "Flagged Zone"
        },
        crossborder: {
            amount: "25000.00",
            currency: "EUR",
            transaction_type: "TRANSFER",
            old_balance_org: "25000.00",
            new_balance_orig: "0.00",
            old_balance_dest: "0.00",
            new_balance_dest: "25000.00",
            step: "1",
            sender_account: "AC-77889900",
            receiver_account: "AC-33445566",
            device_type: "Web",
            location: "International"
        }
    };

    const presetButtons = document.querySelectorAll("[data-preset]");
    presetButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const presetKey = btn.getAttribute("data-preset");
            const data = presets[presetKey];
            if (!data) return;

            Object.keys(data).forEach(fieldId => {
                const el = document.getElementById(fieldId);
                if (el) {
                    el.value = data[fieldId];
                    el.style.borderColor = "var(--accent-blue)";
                    setTimeout(() => el.style.borderColor = "", 400);
                }
            });
            window.showToast(`Loaded "${presetKey.toUpperCase()}" scenario values`, "info");
        });
    });

    // 5. Interactive AJAX Prediction Form Submission
    const predictForm = document.getElementById("predictionForm");
    const submitBtn = document.getElementById("submitBtn");
    const btnSpinner = document.getElementById("btnSpinner");
    const btnText = document.getElementById("btnText");
    const outcomeContainer = document.getElementById("ajaxOutcomeContainer");

    if (predictForm && outcomeContainer) {
        predictForm.addEventListener("submit", (e) => {
            // Check client-side validation first
            const amountInput = document.getElementById("amount");
            const amt = parseFloat(amountInput?.value);
            if (!amt || amt <= 0 || isNaN(amt)) {
                e.preventDefault();
                window.showToast("Please enter a valid amount greater than 0.", "error");
                amountInput.focus();
                return;
            }

            // If JavaScript is running, prevent full-page reload and score via AJAX
            e.preventDefault();

            // Set loading state
            if (submitBtn) submitBtn.disabled = true;
            if (btnSpinner) btnSpinner.style.display = "inline-block";
            if (btnText) btnText.innerText = "Evaluating Real-Time Telemetry...";

            const preAnalysisCard = document.getElementById("preAnalysisCard");
            const loadingCard = document.getElementById("predictLoadingCard");
            if (preAnalysisCard) preAnalysisCard.style.display = "none";
            if (loadingCard) loadingCard.style.display = "block";
            if (outcomeContainer) outcomeContainer.innerHTML = "";

            const payload = {
                amount: amt,
                currency: document.getElementById("currency")?.value || "USD",
                transaction_type: document.getElementById("transaction_type")?.value || "PAYMENT",
                old_balance_org: parseFloat(document.getElementById("old_balance_org")?.value || "0") || 0.0,
                new_balance_orig: parseFloat(document.getElementById("new_balance_orig")?.value || "0") || 0.0,
                old_balance_dest: parseFloat(document.getElementById("old_balance_dest")?.value || "0") || 0.0,
                new_balance_dest: parseFloat(document.getElementById("new_balance_dest")?.value || "0") || 0.0,
                step: parseFloat(document.getElementById("step")?.value || "1") || 1.0,
                sender_account: document.getElementById("sender_account")?.value || "",
                receiver_account: document.getElementById("receiver_account")?.value || "",
                device_type: document.getElementById("device_type")?.value || "Web",
                location: document.getElementById("location")?.value || "Domestic"
            };

            fetch("/api/predict", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(result => {
                // Hide server-side rendered fallback card if present
                const serverCard = document.getElementById("serverOutcomeCard");
                if (serverCard) serverCard.style.display = "none";
                if (loadingCard) loadingCard.style.display = "none";

                if (result.status === "error") {
                    const errs = result.errors ? result.errors.join("<br>") : result.message;
                    outcomeContainer.innerHTML = `
                        <div class="alert alert-danger" style="margin-top: 1.5rem;">
                            <strong>Inference Error:</strong> ${errs}
                        </div>
                    `;
                    window.showToast("Transaction validation failed.", "error");
                    return;
                }

                const isFraud = result.is_fraud;
                const riskTier = result.risk_level || (isFraud ? "Critical" : "Low");
                const prob = Number(result.fraud_probability || 0) * 100;
                const perimeter = 364.4;
                const offset = Math.max(0, perimeter - (perimeter * (prob / 100.0)));
                const strokeColor = isFraud ? '#ef4444' : (prob > 35 ? '#f59e0b' : '#10b981');
                const normDisplay = result.currency !== "USD" && result.normalized_amount_usd
                    ? `<div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;"><span style="color: var(--text-muted);">Normalized (USD):</span><span>$${Number(result.normalized_amount_usd).toFixed(2)}</span></div>`
                    : "";

                outcomeContainer.innerHTML = `
                    <div class="risk-gauge-box ${isFraud ? 'is-fraud' : 'is-legitimate'}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
                            <span class="risk-level-badge risk-${riskTier.toLowerCase()}">
                                Risk Tier: ${riskTier}
                            </span>
                            <span class="badge ${isFraud ? 'badge-fraud' : 'badge-safe'}">
                                ${isFraud ? '🚨 FRAUD DETECTED' : '✅ LEGITIMATE'}
                            </span>
                        </div>

                        <!-- Circular Gauge Visualization -->
                        <div class="gauge-svg-container">
                            <svg class="gauge-svg" viewBox="0 0 140 140">
                                <circle class="gauge-track" cx="70" cy="70" r="58" />
                                <circle class="gauge-fill" cx="70" cy="70" r="58"
                                        stroke-dasharray="364.4"
                                        stroke-dashoffset="${offset.toFixed(1)}"
                                        style="stroke: ${strokeColor};" />
                            </svg>
                            <div class="gauge-center-text">
                                <span class="gauge-percent" style="color: ${strokeColor};">${prob.toFixed(1)}%</span>
                                <span class="gauge-label">Fraud Risk</span>
                            </div>
                        </div>

                        <h3 style="font-size: 1.35rem; font-weight: 800; margin: 0 0 0.5rem; color: #ffffff;">
                            Decision: ${result.prediction_label}
                        </h3>

                        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem; margin: 1rem 0; font-size: 0.85rem; text-align: left;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span style="color: var(--text-muted);">Reference:</span>
                                <span style="font-family: monospace; color: #cbd5e1;">
                                    ${result.transaction_ref}
                                    <button type="button" class="copy-btn" onclick="copyText('${result.transaction_ref}', this)">Copy</button>
                                </span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span style="color: var(--text-muted);">Submitted Amount:</span>
                                <strong>${Number(result.original_amount).toFixed(2)} ${result.currency}</strong>
                            </div>
                            ${normDisplay}
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-muted);">Inference Latency:</span>
                                <span style="color: #14b8a6; font-weight: 600;">${result.latency_ms || 1.2} ms</span>
                            </div>
                        </div>

                        <div style="font-size: 0.78rem; color: var(--text-muted); border-top: 1px solid var(--border-subtle); padding-top: 0.85rem; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
                            <span>Engine: <em>${result.model_info?.name || 'ExtraTrees'}</em></span>
                            <span>Ledger: <strong>Persisted</strong></span>
                        </div>

                        <div style="margin-top: 1.25rem; display: flex; gap: 0.75rem;">
                            <button type="button" class="btn btn-secondary" onclick="resetPredictionWorkspace()" style="flex: 1; font-size: 0.85rem; padding: 0.65rem;">
                                Analyze Another
                            </button>
                            <a href="/dashboard" class="btn btn-primary" style="flex: 1; font-size: 0.85rem; padding: 0.65rem; text-decoration: none; text-align: center;">
                                View Dashboard
                            </a>
                        </div>
                    </div>
                `;

                window.showToast("Transaction evaluated & saved to audit ledger!", "success");
                outcomeContainer.scrollIntoView({ behavior: "smooth", block: "nearest" });
            })
            .catch(err => {
                if (loadingCard) loadingCard.style.display = "none";
                outcomeContainer.innerHTML = `
                    <div class="alert alert-danger" style="margin-top: 1.5rem;">
                        <strong>Communication Error:</strong> Could not reach prediction service (${err.message}).
                    </div>
                `;
                window.showToast("Inference request failed.", "error");
            })
            .finally(() => {
                if (submitBtn) submitBtn.disabled = false;
                if (btnSpinner) btnSpinner.style.display = "none";
                if (btnText) btnText.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="vertical-align: -3px; margin-right: 6px;"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> Execute ML Fraud Risk Analysis`;
            });
        });
    }

    // 6. Interactive History Table Controller (Live Filters & Pagination on /dashboard)
    const tableEl = document.getElementById("transactionsTable");
    const tbody = document.getElementById("transactionsTbody");
    const searchInput = document.getElementById("tableSearch");
    const filterStatus = document.getElementById("filterStatus");
    const filterCurrency = document.getElementById("filterCurrency");
    const filterSort = document.getElementById("filterSort");
    const refreshBtn = document.getElementById("refreshTableBtn");
    const prevPageBtn = document.getElementById("prevPageBtn");
    const nextPageBtn = document.getElementById("nextPageBtn");
    const pageInfo = document.getElementById("pageInfo");
    const countBadge = document.getElementById("tableCountBadge");

    if (tableEl && tbody) {
        let currentPage = 1;
        const perPage = 20;
        let totalPages = 1;
        let totalRecords = 0;

        function loadHistoryData(page = 1) {
            currentPage = page;
            const searchVal = searchInput ? searchInput.value.trim() : "";
            const statusVal = filterStatus ? filterStatus.value : "";
            const currVal = filterCurrency ? filterCurrency.value : "";
            const sortVal = filterSort ? filterSort.value : "created_at_desc";

            let sortBy = "created_at";
            let sortDir = "desc";
            if (sortVal === "amount_desc") { sortBy = "amount"; sortDir = "desc"; }
            else if (sortVal === "amount_asc") { sortBy = "amount"; sortDir = "asc"; }
            else if (sortVal === "confidence_desc") { sortBy = "confidence_score"; sortDir = "desc"; }

            let url = `/api/predictions?page=${currentPage}&per_page=${perPage}&sort_by=${sortBy}&order=${sortDir}`;
            if (searchVal) url += `&ref=${encodeURIComponent(searchVal)}`;
            if (statusVal) url += `&status=${encodeURIComponent(statusVal)}`;
            if (currVal) url += `&currency=${encodeURIComponent(currVal)}`;

            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
                        <div class="spinner" style="margin-right: 0.5rem;"></div> Querying SQLite ledger records...
                    </td>
                </tr>
            `;

            fetch(url)
                .then(res => res.json())
                .then(data => {
                    if (!data.success) throw new Error(data.error || "Failed to query records");

                    totalPages = data.total_pages || 1;
                    totalRecords = data.total || 0;

                    if (countBadge) countBadge.innerText = `Showing ${data.count} of ${totalRecords} total transactions`;
                    if (pageInfo) pageInfo.innerText = `Page ${data.page} of ${totalPages} • ${totalRecords} Records`;

                    if (prevPageBtn) prevPageBtn.disabled = (currentPage <= 1);
                    if (nextPageBtn) nextPageBtn.disabled = (currentPage >= totalPages);

                    if (!data.predictions || data.predictions.length === 0) {
                        tbody.innerHTML = `
                            <tr>
                                <td colspan="9" style="text-align: center; padding: 3rem 1.5rem; color: var(--text-secondary);">
                                    <p style="font-size: 1.05rem; margin-bottom: 0.5rem;">No matching transactions found.</p>
                                    <span style="font-size: 0.85rem; color: var(--text-muted);">Try adjusting your search or filter options.</span>
                                </td>
                            </tr>
                        `;
                        return;
                    }

                    tbody.innerHTML = data.predictions.map(t => {
                        const isFraud = t.is_fraud;
                        const riskClass = (t.risk_level || 'low').toLowerCase();
                        const normStr = t.currency !== 'USD' && t.normalized_amount
                            ? `<div style="font-size: 0.75rem; color: var(--text-muted);">$${Number(t.normalized_amount).toFixed(2)} USD</div>`
                            : '';

                        return `
                            <tr data-ref="${t.transaction_ref}" data-id="${t.id}">
                                <td>
                                    <code>${t.transaction_ref}</code>
                                    <button type="button" class="copy-btn" onclick="copyText('${t.transaction_ref}', this)" title="Copy Reference">📋</button>
                                </td>
                                <td style="color: var(--text-muted); font-size: 0.85rem;">
                                    ${t.created_at || 'Recent'}
                                </td>
                                <td><strong>${t.transaction_type}</strong></td>
                                <td>
                                    <strong>${Number(t.amount).toFixed(2)} ${t.currency || 'USD'}</strong>
                                    ${normStr}
                                </td>
                                <td style="font-size: 0.82rem; color: var(--text-secondary);">
                                    ${t.sender_account || 'N/A'} &rarr; ${t.receiver_account || 'N/A'}
                                </td>
                                <td>
                                    <span class="risk-level-badge risk-${riskClass}" style="font-size: 0.75rem; padding: 0.2rem 0.55rem; margin-bottom: 0;">
                                        ${t.risk_level || 'Low'}
                                    </span>
                                </td>
                                <td>
                                    <strong>${Number(t.confidence_score || 0).toFixed(1)}%</strong>
                                </td>
                                <td>
                                    <span class="badge ${isFraud ? 'badge-fraud' : 'badge-safe'}">
                                        ${t.prediction_label || (isFraud ? 'Fraudulent' : 'Legitimate')}
                                    </span>
                                </td>
                                <td style="text-align: right;">
                                    <button type="button" class="btn btn-secondary" style="padding: 0.3rem 0.65rem; font-size: 0.8rem;"
                                            onclick="inspectTransaction('${t.transaction_ref}')">
                                        🔍 Inspect
                                    </button>
                                </td>
                            </tr>
                        `;
                    }).join("");
                })
                .catch(err => {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="9" style="text-align: center; padding: 2rem; color: var(--status-fraud);">
                                Failed to load transactions: ${err.message}
                            </td>
                        </tr>
                    `;
                });
        }

        // Debounced Search Input
        let searchTimeout = null;
        if (searchInput) {
            searchInput.addEventListener("input", () => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => loadHistoryData(1), 350);
            });
        }

        // Filter Dropdowns
        if (filterStatus) filterStatus.addEventListener("change", () => loadHistoryData(1));
        if (filterCurrency) filterCurrency.addEventListener("change", () => loadHistoryData(1));
        if (filterSort) filterSort.addEventListener("change", () => loadHistoryData(1));
        if (refreshBtn) refreshBtn.addEventListener("click", () => {
            loadHistoryData(currentPage);
            window.showToast("Refreshed transaction records from SQLite", "info");
        });

        // Pagination Buttons
        if (prevPageBtn) {
            prevPageBtn.addEventListener("click", () => {
                if (currentPage > 1) loadHistoryData(currentPage - 1);
            });
        }
        if (nextPageBtn) {
            nextPageBtn.addEventListener("click", () => {
                if (currentPage < totalPages) loadHistoryData(currentPage + 1);
            });
        }
    }

    // 7. Advanced Fraud Analytics Dashboard Controller (Prompt 7)
    const chartFraudVsSafeEl = document.getElementById("chartFraudVsSafe");
    if (chartFraudVsSafeEl) {
        let chartFraudVsSafeInst = null;
        let chartFraudTrendInst = null;
        let chartCurrencyDistInst = null;
        let chartRiskDistInst = null;
        let currentTrendDays = null;

        const refreshAnalyticsBtn = document.getElementById("refreshAnalyticsBtn");
        const refreshSpinner = document.getElementById("refreshSpinner");
        const refreshBtnIcon = document.getElementById("refreshBtnIcon");
        const refreshBtnText = document.getElementById("refreshBtnText");

        // Enterprise AI + Fintech Dark Theme Chart.js Defaults
        const chartTheme = {
            textColor: "#94a3b8",
            gridColor: "rgba(255, 255, 255, 0.06)",
            font: { family: "'Inter', system-ui, -apple-system, sans-serif", size: 11 },
            tooltip: {
                backgroundColor: "#070a10",
                titleColor: "#f8fafc",
                bodyColor: "#94a3b8",
                borderColor: "#283548",
                borderWidth: 1,
                padding: 10,
                cornerRadius: 8
            }
        };

        function updateCharts(data) {
            if (typeof Chart === "undefined") {
                console.warn("Chart.js library is not yet loaded.");
                return;
            }

            // 1. Chart: Fraud vs Safe Distribution (Doughnut)
            const fvs = data.fraud_vs_safe;
            const ctxFvs = chartFraudVsSafeEl.getContext("2d");
            if (chartFraudVsSafeInst) {
                chartFraudVsSafeInst.data.datasets[0].data = [fvs.safe_count, fvs.fraud_count];
                chartFraudVsSafeInst.update();
            } else {
                chartFraudVsSafeInst = new Chart(ctxFvs, {
                    type: "doughnut",
                    data: {
                        labels: ["Legitimate Approved", "Fraudulent Detected"],
                        datasets: [{
                            data: [fvs.safe_count, fvs.fraud_count],
                            backgroundColor: ["#10b981", "#ef4444"],
                            borderColor: ["#111827", "#111827"],
                            borderWidth: 3,
                            hoverOffset: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: "68%",
                        plugins: {
                            legend: {
                                position: "bottom",
                                labels: { color: chartTheme.textColor, font: chartTheme.font, padding: 16 }
                            },
                            tooltip: {
                                ...chartTheme.tooltip,
                                callbacks: {
                                    label: function(ctx) {
                                        const count = ctx.parsed;
                                        const total = fvs.total || (fvs.safe_count + fvs.fraud_count);
                                        const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                                        return ` ${ctx.label}: ${count} (${pct}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            }

            // 2. Chart: Fraud Trend Over Time (Line)
            const trendCanvas = document.getElementById("chartFraudTrend");
            if (trendCanvas) {
                const points = data.trend.points || [];
                const labels = points.map(p => p.date);
                const safeSeries = points.map(p => p.safe);
                const fraudSeries = points.map(p => p.fraud);
                const totalSeries = points.map(p => p.total);

                const ctxTrend = trendCanvas.getContext("2d");
                if (chartFraudTrendInst) {
                    chartFraudTrendInst.data.labels = labels;
                    chartFraudTrendInst.data.datasets[0].data = totalSeries;
                    chartFraudTrendInst.data.datasets[1].data = safeSeries;
                    chartFraudTrendInst.data.datasets[2].data = fraudSeries;
                    chartFraudTrendInst.update();
                } else {
                    chartFraudTrendInst = new Chart(ctxTrend, {
                        type: "line",
                        data: {
                            labels: labels,
                            datasets: [
                                {
                                    label: "Total Predictions",
                                    data: totalSeries,
                                    borderColor: "#14b8a6",
                                    backgroundColor: "rgba(20, 184, 166, 0.08)",
                                    borderWidth: 2,
                                    tension: 0.3,
                                    fill: true,
                                    pointRadius: 4,
                                    pointHoverRadius: 6
                                },
                                {
                                    label: "Safe Transactions",
                                    data: safeSeries,
                                    borderColor: "#10b981",
                                    backgroundColor: "transparent",
                                    borderWidth: 2,
                                    tension: 0.3,
                                    pointRadius: 4,
                                    pointHoverRadius: 6
                                },
                                {
                                    label: "Fraud Caught",
                                    data: fraudSeries,
                                    borderColor: "#ef4444",
                                    backgroundColor: "transparent",
                                    borderWidth: 2,
                                    tension: 0.3,
                                    pointRadius: 4,
                                    pointHoverRadius: 6
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: "bottom",
                                    labels: { color: chartTheme.textColor, font: chartTheme.font, padding: 14 }
                                },
                                tooltip: chartTheme.tooltip
                            },
                            scales: {
                                x: {
                                    grid: { color: chartTheme.gridColor },
                                    ticks: { color: chartTheme.textColor, font: chartTheme.font }
                                },
                                y: {
                                    beginAtZero: true,
                                    grid: { color: chartTheme.gridColor },
                                    ticks: { color: chartTheme.textColor, font: chartTheme.font, precision: 0 }
                                }
                            }
                        }
                    });
                }
            }

            // 3. Chart: Currency Distribution (Bar)
            const currCanvas = document.getElementById("chartCurrencyDist");
            if (currCanvas) {
                const currs = data.currency_distribution || [];
                const currLabels = currs.map(c => c.currency);
                const currCounts = currs.map(c => c.count);
                const palette = ["#10b981", "#14b8a6", "#1f2937", "#374151", "#64748b", "#f59e0b", "#0d9488"];

                const ctxCurr = currCanvas.getContext("2d");
                if (chartCurrencyDistInst) {
                    chartCurrencyDistInst.data.labels = currLabels;
                    chartCurrencyDistInst.data.datasets[0].data = currCounts;
                    chartCurrencyDistInst.update();
                } else {
                    chartCurrencyDistInst = new Chart(ctxCurr, {
                        type: "bar",
                        data: {
                            labels: currLabels,
                            datasets: [{
                                label: "Transactions",
                                data: currCounts,
                                backgroundColor: palette.slice(0, currLabels.length),
                                borderRadius: 6
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false },
                                tooltip: {
                                    ...chartTheme.tooltip,
                                    callbacks: {
                                        label: function(ctx) {
                                            const item = currs[ctx.dataIndex];
                                            return ` Volume: ${ctx.parsed.y} (${item ? item.percentage : 0}%)`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    grid: { display: false },
                                    ticks: { color: chartTheme.textColor, font: chartTheme.font }
                                },
                                y: {
                                    beginAtZero: true,
                                    grid: { color: chartTheme.gridColor },
                                    ticks: { color: chartTheme.textColor, font: chartTheme.font, precision: 0 }
                                }
                            }
                        }
                    });
                }
            }

            // 4. Chart: Risk Level Distribution (Doughnut / Polar)
            const riskCanvas = document.getElementById("chartRiskDist");
            if (riskCanvas) {
                const risks = data.risk_distribution || [];
                const riskLabels = risks.map(r => r.risk_level);
                const riskCounts = risks.map(r => r.count);
                const riskColorMap = {
                    "low": "#10b981",
                    "moderate": "#f59e0b",
                    "medium": "#f59e0b",
                    "high": "#f97316",
                    "critical": "#ef4444"
                };
                const riskColors = riskLabels.map(lvl => riskColorMap[lvl.toLowerCase()] || "#64748b");

                const ctxRisk = riskCanvas.getContext("2d");
                if (chartRiskDistInst) {
                    chartRiskDistInst.data.labels = riskLabels;
                    chartRiskDistInst.data.datasets[0].data = riskCounts;
                    chartRiskDistInst.data.datasets[0].backgroundColor = riskColors;
                    chartRiskDistInst.update();
                } else {
                    chartRiskDistInst = new Chart(ctxRisk, {
                        type: "doughnut",
                        data: {
                            labels: riskLabels,
                            datasets: [{
                                data: riskCounts,
                                backgroundColor: riskColors,
                                borderColor: "#111827",
                                borderWidth: 2,
                                hoverOffset: 5
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            cutout: "60%",
                            plugins: {
                                legend: {
                                    position: "bottom",
                                    labels: { color: chartTheme.textColor, font: chartTheme.font, padding: 14 }
                                },
                                tooltip: {
                                    ...chartTheme.tooltip,
                                    callbacks: {
                                        label: function(ctx) {
                                            const item = risks[ctx.dataIndex];
                                            return ` ${ctx.label}: ${ctx.parsed} transactions (${item ? item.percentage : 0}%)`;
                                        }
                                    }
                                }
                            }
                        }
                    });
                }
            }
        }

        function updateSummaryCards(summary) {
            if (!summary) return;
            const elTotal = document.getElementById("kpiTotal");
            const elFraud = document.getElementById("kpiFraud");
            const elLegit = document.getElementById("kpiLegit");
            const elRate = document.getElementById("kpiRate");
            const elAvg = document.getElementById("kpiAvgAmount");
            const elMax = document.getElementById("kpiMaxAmount");
            const elModel = document.getElementById("kpiModel");

            if (elTotal) elTotal.innerText = summary.total_predictions;
            if (elFraud) elFraud.innerText = summary.fraudulent_predictions;
            if (elLegit) elLegit.innerText = summary.safe_predictions;
            if (elRate) elRate.innerText = `${summary.fraud_percentage.toFixed(2)}%`;
            if (elAvg) elAvg.innerText = `$${summary.average_amount_usd.toFixed(2)}`;
            if (elMax) elMax.innerText = `$${summary.highest_amount_usd.toFixed(2)}`;
            if (elModel) elModel.innerText = summary.current_model;

            const elTodayCount = document.getElementById("kpiTodayCount");
            if (elTodayCount) elTodayCount.innerText = summary.today_predictions !== undefined ? summary.today_predictions : 0;
            const elSevenDayCount = document.getElementById("kpiSevenDayCount");
            if (elSevenDayCount) elSevenDayCount.innerText = summary.seven_day_predictions !== undefined ? summary.seven_day_predictions : 0;
        }

        function updateCurrencyTable(breakdown) {
            const tbody = document.getElementById("currencyTableBody");
            if (!tbody || !breakdown) return;
            if (breakdown.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No currency transaction data recorded yet.</td></tr>`;
                return;
            }

            tbody.innerHTML = breakdown.map(c => `
                <tr>
                    <td><span class="currency-badge">${c.currency}</span></td>
                    <td><strong>${c.count}</strong></td>
                    <td><span style="color: var(--status-fraud); font-weight: 600;">${c.fraud_count}</span></td>
                    <td><span style="color: var(--status-safe); font-weight: 600;">${c.safe_count}</span></td>
                    <td><strong>${Number(c.total_amount).toFixed(2)} ${c.currency}</strong></td>
                    <td>${Number(c.avg_amount).toFixed(2)} ${c.currency}</td>
                    <td style="color: var(--text-muted);">${Number(c.min_amount).toFixed(2)} ${c.currency}</td>
                    <td><strong>${Number(c.max_amount).toFixed(2)} ${c.currency}</strong></td>
                    <td>${Number(c.percentage).toFixed(1)}%</td>
                </tr>
            `).join("");
        }

        function updateRecentActivity(recentList) {
            const tbody = document.getElementById("recentActivityTbody");
            if (!tbody || !recentList) return;
            if (recentList.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-muted);">No recent predictions found in database.</td></tr>`;
                return;
            }

            tbody.innerHTML = recentList.map(t => {
                const isFraud = t.is_fraud;
                const riskClass = (t.risk_level || 'low').toLowerCase();
                const normStr = t.currency !== 'USD' && t.normalized_amount
                    ? `<div style="font-size: 0.75rem; color: var(--text-muted);">$${Number(t.normalized_amount).toFixed(2)} USD</div>`
                    : '';

                return `
                    <tr>
                        <td>
                            <code>${t.transaction_ref}</code>
                            <button type="button" class="copy-btn" onclick="copyText('${t.transaction_ref}', this)" title="Copy Reference">📋</button>
                        </td>
                        <td style="color: var(--text-muted); font-size: 0.85rem;">
                            ${t.created_at || 'Recent'}
                        </td>
                        <td><strong>${t.transaction_type}</strong></td>
                        <td>
                            <strong>${Number(t.amount).toFixed(2)} ${t.currency || 'USD'}</strong>
                            ${normStr}
                        </td>
                        <td>
                            <span class="risk-level-badge risk-${riskClass}" style="font-size: 0.75rem; padding: 0.2rem 0.55rem; margin-bottom: 0;">
                                ${t.risk_level || 'Low'}
                            </span>
                        </td>
                        <td>
                            <strong>${Number(t.confidence_score || 0).toFixed(1)}%</strong>
                        </td>
                        <td>
                            <span class="badge ${isFraud ? 'badge-fraud' : 'badge-safe'}">
                                ${t.prediction_label || (isFraud ? 'Fraudulent' : 'Legitimate')}
                            </span>
                        </td>
                        <td style="text-align: right;">
                            <button type="button" class="btn btn-secondary btn-sm" style="padding: 0.3rem 0.65rem; font-size: 0.8rem;"
                                    onclick="inspectTransaction('${t.transaction_ref}')">
                                View Details
                            </button>
                        </td>
                    </tr>
                `;
            }).join("");
        }

        function updateAlertsList(alerts) {
            const list = document.getElementById("ficAlertsList");
            if (!list) return;
            if (!alerts || alerts.length === 0) {
                list.innerHTML = `
                    <div class="fic-empty-alerts">
                        <span class="fic-check-icon">✓</span>
                        <p>No active fraud alerts</p>
                        <span class="fic-empty-sub">All evaluated transactions conform to normal baseline risk parameters.</span>
                    </div>
                `;
                return;
            }
            list.innerHTML = alerts.map(a => {
                const sev = a.severity || (a.is_fraud ? "critical" : "medium");
                const riskLvl = (a.risk_level || "HIGH").toUpperCase();
                return `
                    <div class="fic-alert-item alert-${sev}">
                        <div class="fic-alert-top">
                            <div class="fic-alert-ref-wrap">
                                <span class="fic-severity-tag tag-${sev}">${riskLvl}</span>
                                <code class="fic-alert-ref">${a.ref}</code>
                            </div>
                            <span class="fic-alert-score">${a.risk_score}% Risk</span>
                        </div>
                        <div class="fic-alert-body">
                            <div class="fic-alert-amount">
                                <strong>${Number(a.amount).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} ${a.currency}</strong>
                                <span class="fic-alert-type">${a.transaction_type || 'TRANSFER'}</span>
                            </div>
                            <div class="fic-alert-time">${a.created_at || 'Recent'}</div>
                        </div>
                    </div>
                `;
            }).join("");
        }

        function updateInsightsList(insights) {
            const list = document.getElementById("ficInsightsList");
            if (!list) return;
            if (!insights || insights.length === 0) {
                list.innerHTML = `
                    <p style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem;">
                        Insufficient transaction history to derive statistical patterns.
                    </p>
                `;
                return;
            }
            list.innerHTML = insights.map(ins => `
                <div class="fic-insight-row">
                    <span class="fic-insight-badge badge-${(ins.category || 'info').toLowerCase()}">${ins.badge}</span>
                    <p class="fic-insight-text">${ins.text}</p>
                </div>
            `).join("");
        }

        function fetchAnalytics(days = currentTrendDays, isManual = false) {
            if (isManual) {
                if (refreshSpinner) refreshSpinner.style.display = "inline-block";
                if (refreshBtnIcon) refreshBtnIcon.style.display = "none";
                if (refreshBtnText) refreshBtnText.innerText = "Refreshing...";
                if (refreshAnalyticsBtn) refreshAnalyticsBtn.disabled = true;
            }

            const filterDaysEl = document.getElementById("globalFilterDays");
            const filterCurrEl = document.getElementById("globalFilterCurrency");
            const filterStatusEl = document.getElementById("globalFilterStatus");
            const filterRiskEl = document.getElementById("globalFilterRisk");

            const params = new URLSearchParams();
            const effectiveDays = (days !== undefined && days !== null) ? days : (filterDaysEl ? filterDaysEl.value : null);
            if (effectiveDays) params.set("days", effectiveDays);
            if (filterCurrEl && filterCurrEl.value) params.set("currency", filterCurrEl.value);
            if (filterStatusEl && filterStatusEl.value) params.set("status", filterStatusEl.value);
            if (filterRiskEl && filterRiskEl.value) params.set("risk_level", filterRiskEl.value);

            let url = "/api/analytics/summary";
            const queryString = params.toString();
            if (queryString) url += `?${queryString}`;

            fetch(url)
                .then(res => {
                    if (!res.ok) throw new Error("Analytics API returned HTTP " + res.status);
                    return res.json();
                })
                .then(data => {
                    if (!data.success) throw new Error(data.error || "Analytics generation error");

                    updateSummaryCards(data.summary);
                    updateCharts(data);
                    updateCurrencyTable(data.amount_analytics?.per_currency_breakdown);
                    updateRecentActivity(data.recent_predictions);
                    updateAlertsList(data.fraud_alerts);
                    updateInsightsList(data.ai_insights);

                    const currCountBadge = document.getElementById("currencyCountBadge");
                    if (currCountBadge && data.summary) currCountBadge.innerText = `${data.summary.active_currencies_count} Active`;

                    const alertCountChip = document.getElementById("ficAlertCountChip");
                    if (alertCountChip) alertCountChip.innerText = `${data.fraud_alerts ? data.fraud_alerts.length : 0} Anomaly Alerts`;

                    if (isManual) {
                        window.showToast("Refreshed all analytics and charts with real database data!", "success");
                    }
                })
                .catch(err => {
                    console.error("Failed to refresh analytics:", err);
                    if (isManual) {
                        window.showToast("Could not refresh analytics: " + err.message, "error");
                    }
                })
                .finally(() => {
                    if (isManual) {
                        if (refreshSpinner) refreshSpinner.style.display = "none";
                        if (refreshBtnIcon) refreshBtnIcon.style.display = "inline-block";
                        if (refreshBtnText) refreshBtnText.innerText = "Refresh Data";
                        if (refreshAnalyticsBtn) refreshAnalyticsBtn.disabled = false;
                    }
                });
        }

        // Period filter buttons listener
        const timelineButtons = document.querySelectorAll(".fic-timeline-switch .btn-period, #trendPeriodSelector button[data-days]");
        if (timelineButtons.length > 0) {
            timelineButtons.forEach(btn => {
                btn.addEventListener("click", () => {
                    timelineButtons.forEach(b => b.classList.remove("active"));
                    btn.classList.add("active");

                    const daysVal = btn.getAttribute("data-days");
                    currentTrendDays = (!daysVal || daysVal === "all") ? null : parseInt(daysVal, 10);
                    const filterDaysEl = document.getElementById("globalFilterDays");
                    if (filterDaysEl) filterDaysEl.value = currentTrendDays || "";
                    fetchAnalytics(currentTrendDays, false);
                });
            });
        }

        // Global Filter inputs listener
        const filterIds = ["globalFilterDays", "globalFilterCurrency", "globalFilterStatus", "globalFilterRisk"];
        filterIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener("change", () => {
                    const filterDaysEl = document.getElementById("globalFilterDays");
                    currentTrendDays = filterDaysEl && filterDaysEl.value ? parseInt(filterDaysEl.value, 10) : null;
                    timelineButtons.forEach(b => {
                        const bDays = b.getAttribute("data-days");
                        b.classList.toggle("active", (String(currentTrendDays || "") === String(bDays || "")));
                    });
                    fetchAnalytics(currentTrendDays, false);
                });
            }
        });

        // Reset Filters Button
        const btnReset = document.getElementById("btnResetFilters");
        if (btnReset) {
            btnReset.addEventListener("click", () => {
                filterIds.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.value = "";
                });
                currentTrendDays = null;
                timelineButtons.forEach(b => {
                    const bDays = b.getAttribute("data-days");
                    b.classList.toggle("active", bDays === "" || bDays === "all");
                });
                fetchAnalytics(null, false);
            });
        }

        // Refresh button click listener
        if (refreshAnalyticsBtn) {
            refreshAnalyticsBtn.addEventListener("click", () => {
                fetchAnalytics(currentTrendDays, true);
                if (typeof loadHistoryData === "function") {
                    loadHistoryData(1);
                }
            });
        }

        // Initialize Analytics on page load
        fetchAnalytics(null, false);
    }
});

// Platform Settings & Preferences Modal Handlers
window.openSettingsModal = function() {
    const modal = document.getElementById("settingsModal");
    if (modal) modal.classList.add("active");
};

window.closeSettingsModal = function() {
    const modal = document.getElementById("settingsModal");
    if (modal) modal.classList.remove("active");
};

window.savePlatformPreferences = function() {
    const intervalSelect = document.getElementById("prefRefreshInterval");
    const densitySelect = document.getElementById("prefDensity");
    if (intervalSelect && densitySelect) {
        localStorage.setItem("fg_pref_interval", intervalSelect.value);
        localStorage.setItem("fg_pref_density", densitySelect.value);
        window.closeSettingsModal();
        window.showToast("Preferences successfully saved.", "success");
    }
};
