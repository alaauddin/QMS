/**
 * Dashboard Logic for QMS Operator
 * Dependent on window.QMS_CONFIG (populated in the template)
 */

document.addEventListener('DOMContentLoaded', function() {
    const config = window.QMS_CONFIG;
    if (!config) {
        console.error("QMS_CONFIG not found. Dashboard logic will not initialize.");
        return;
    }

    // Keep the queue current when a ticket is issued, even after a socket drop.
    let socket = null;
    let reconnectTimer = null;
    let refreshTimer = null;
    let latestDashboardRequest = 0;

    function scheduleDashboardRefresh() {
        if (refreshTimer) clearTimeout(refreshTimer);
        refreshTimer = setTimeout(() => {
            refreshTimer = null;
            updateDashboardUI();
        }, 100);
    }

    function connectDashboardSocket() {
        if (!window.WebSocket || !config.counterIds.length) return;
        const wsUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') +
            window.location.host + '/ws/counter/' + config.counterIds[0] + '/';
        let connection;
        try {
            connection = new WebSocket(wsUrl);
        } catch (error) {
            scheduleReconnect();
            return;
        }
        socket = connection;
        connection.onopen = scheduleDashboardRefresh;
        connection.onmessage = function(e) {
            let data;
            try {
                data = JSON.parse(e.data);
            } catch (error) {
                return;
            }

            if (data.type === 'token_issued' || data.type === 'queue_changed' ||
                data.type === 'token_called' || data.type === 'token_cleared') {
                scheduleDashboardRefresh();
            }
            if (data.type === 'token_called' && data.audio) {
                playAnnouncement(data.audio);
            } else if (data.type === 'token_audio' &&
                       config.counterIds.some(id => String(id) === String(data.counter_id)) &&
                       data.audio) {
                playAnnouncement(data.audio);
            }
        };
        connection.onclose = function() {
            if (socket === connection) socket = null;
            scheduleReconnect();
        };
        connection.onerror = function() {
            connection.close();
        };
    }

    function scheduleReconnect() {
        if (reconnectTimer) return;
        reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            connectDashboardSocket();
        }, 3000);
    }

    connectDashboardSocket();
    setInterval(updateDashboardUI, 15000);

    // Make functions globally available if needed by onclick handlers
    window.handleAction = handleAction;
    window.updateDashboardUI = updateDashboardUI;
    window.resumeToken = resumeToken;
    window.openTransferModal = openTransferModal;
    window.confirmTransfer = confirmTransfer;

    function playAnnouncement(base64Audio) {
        const audio = document.getElementById('announcement-audio');
        if (audio) {
            audio.src = 'data:audio/mp3;base64,' + base64Audio;
            audio.play().catch(e => console.log("Audio blocked by browser, interaction required."));
        }
    }

    function updateDashboardUI() {
        const requestId = ++latestDashboardRequest;
        fetch(config.urls.get_dashboard_data, {cache: 'no-store'})
        .then(res => res.json())
        .then(data => {
            if (requestId !== latestDashboardRequest || data.error) return;

            // Update Stats
            document.getElementById('stat-waiting').innerText = data.stats.waiting;
            document.getElementById('stat-served').innerText = data.stats.served;
            document.getElementById('stat-avg-time').innerText = data.stats.avg_time;

            // Update Held Count
            document.getElementById('held-count').innerText = data.held.length;

            // Update Current Token
            const tokenEl = document.getElementById('current-token');
            const serviceEl = document.getElementById('current-service');
            
            if (data.current) {
                tokenEl.innerText = data.current.full_token;
                serviceEl.innerText = data.current.service_name;
                tokenEl.classList.remove('text-muted');
                document.getElementById('btn-call-next').disabled = true;
            } else {
                tokenEl.innerText = "--";
                serviceEl.innerText = config.translations.no_active_customer;
                tokenEl.classList.add('text-muted');
                document.getElementById('btn-call-next').disabled = false;
            }

            // Update Queue List
            const queueBody = document.getElementById('queue-body');
            document.getElementById('queue-count').innerText = data.queue.length;
            queueBody.innerHTML = '';
            
            data.queue.forEach(t => {
                queueBody.innerHTML += `
                    <tr class="animate-in">
                        <td style="width: 80px;"><span class="token-badge shadow-sm">${t.prefix}${t.number}</span></td>
                        <td><div class="fw-bold small text-uppercase" style="letter-spacing: 0.5px;">${t.service_name}</div></td>
                        <td class="text-end"><span class="badge rounded-pill bg-light text-muted border px-2 py-1" style="font-weight: 500;">${t.wait_time}m</span></td>
                    </tr>
                `;
            });
            if(data.queue.length === 0) {
                queueBody.innerHTML = `<tr><td class="text-center py-4 text-muted small">${config.translations.queue_empty}</td></tr>`;
            }

            // Update Held List
            const heldBody = document.getElementById('held-body');
            heldBody.innerHTML = '';
            data.held.forEach(t => {
                heldBody.innerHTML += `
                    <tr class="animate-in">
                        <td style="width: 80px;"><span class="token-badge bg-warning text-dark border-0 shadow-sm">${t.prefix}${t.number}</span></td>
                        <td><div class="fw-bold small text-uppercase" style="letter-spacing: 0.5px;">${t.service_name}</div></td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-primary rounded-pill px-3 shadow-sm border-0" onclick="resumeToken(${t.id})" style="background: var(--primary-gradient);">
                                <i class="fas fa-play me-1"></i> ${config.translations.resume}
                            </button>
                        </td>
                    </tr>
                `;
            });
            if(data.held.length === 0) {
                heldBody.innerHTML = `<tr><td class="text-center py-4 text-muted small">${config.translations.no_held_customers}</td></tr>`;
            }

            // Update Transfer Options
            const sSelect = document.getElementById('transfer-service');
            if (sSelect) {
                sSelect.innerHTML = `<option value="">-- ${config.translations.keep_current_service} --</option>` +
                                  data.transfer_options.services.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
            }
            
            const cSelect = document.getElementById('transfer-counter');
            if (cSelect) {
                cSelect.innerHTML = `<option value="">${config.translations.any_counter}</option>` + 
                                  data.transfer_options.counters.map(c => `<option value="${c.id}">${config.translations.counter} ${c.number}</option>`).join('');
            }
        })
        .catch(error => console.error('Dashboard refresh failed:', error));
    }

    function resumeToken(tokenId) {
        const url = config.urls.resume_token_base.replace('0', tokenId);
        fetch(url).then(res => res.json()).then(data => {
            if(data.success) updateDashboardUI();
            else alert(data.error);
        });
    }

    function openTransferModal() {
        const modalEl = document.getElementById('transferModal');
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    }

    function confirmTransfer() {
        const serviceId = document.getElementById('transfer-service').value;
        const counterId = document.getElementById('transfer-counter').value;
        const isPriority = document.getElementById('transfer-priority').checked;

        fetch(config.urls.transfer_token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': config.csrfToken
            },
            body: JSON.stringify({
                service_id: serviceId || null,
                counter_id: counterId || null,
                is_priority: isPriority
            })
        })
        .then(res => res.json())
        .then(data => {
            if(data.success) {
                const modalEl = document.getElementById('transferModal');
                bootstrap.Modal.getInstance(modalEl).hide();
                // Clear display immediately
                document.getElementById('current-token').innerText = "--";
                document.getElementById('current-service').innerText = config.translations.no_active_customer;
                document.getElementById('btn-call-next').disabled = false;
                updateDashboardUI();
            } else {
                alert(data.error);
            }
        });
    }

    function handleAction(action) {
        const loading = document.getElementById('loading');
        const messageEl = document.getElementById('message');
        if (loading) loading.style.display = 'flex';
        if (messageEl) messageEl.innerText = '';

        let url = '';
        switch(action) {
            case 'call_next': url = config.urls.call_next; break;
            case 'recall': url = config.urls.recall; break;
            case 'done': url = config.urls.done; break;
            case 'no-show': url = config.urls.no_show; break;
            case 'hold': url = config.urls.hold; break;
        }

        fetch(url)
        .then(res => res.json())
        .then(data => {
            if (loading) loading.style.display = 'none';
            if(data.error) {
                if (messageEl) {
                    messageEl.className = 'mt-4 fw-bold text-danger animate-in';
                    messageEl.innerText = data.error;
                }
            } else {
                // Clear display immediately for session-ending actions
                if (['done', 'no-show', 'hold'].includes(action)) {
                    document.getElementById('current-token').innerText = "--";
                    document.getElementById('current-service').innerText = config.translations.no_active_customer;
                    document.getElementById('btn-call-next').disabled = false;
                }
                if (action === 'call_next') {
                    document.getElementById('btn-call-next').disabled = true;
                }
                updateDashboardUI();
                if(action === 'call_next' && messageEl) {
                    messageEl.className = 'mt-4 fw-bold text-success animate-in';
                    messageEl.innerText = config.translations.token_called;
                }
            }
        })
        .catch(err => {
            if (loading) loading.style.display = 'none';
            console.error('Action error:', err);
            if (messageEl) {
                messageEl.className = 'mt-4 fw-bold text-danger animate-in';
                messageEl.innerText = config.translations.connection_error;
            }
        });
    }

    // Initial Load
    updateDashboardUI();
});
