document.addEventListener('DOMContentLoaded', () => {
    const fetchBtn = document.getElementById('fetchBtn');
    const videoUrlInput = document.getElementById('videoUrl');
    const errorBox = document.getElementById('errorBox');
    const errorMsg = document.getElementById('errorMsg');
    const metadataContainer = document.getElementById('metadataContainer');
    const skeletonLoader = document.getElementById('skeletonLoader');
    const progressContainer = document.getElementById('progressContainer');
    const queueSection = document.getElementById('queueSection');
    const queueList = document.getElementById('queueList');
    
    // Set to keep track of already notified/downloaded tasks to prevent double triggers
    const completedTasks = new Set();
    
    // Check url parameter for auto-load
    const urlParams = new URLSearchParams(window.location.search);
    const urlParam = urlParams.get('url');
    if (urlParam) {
        videoUrlInput.value = urlParam;
        fetchVideoInfo(urlParam);
    }
    
    // Start polling the queue immediately
    startQueuePolling();
    
    fetchBtn.addEventListener('click', () => {
        const url = videoUrlInput.value.trim();
        if (!url) {
            showError("Please enter a valid URL.");
            return;
        }
        fetchVideoInfo(url);
    });

    function showError(msg) {
        errorMsg.innerText = msg;
        errorBox.style.display = 'block';
        metadataContainer.style.display = 'none';
        progressContainer.style.display = 'none';
        if (skeletonLoader) skeletonLoader.style.display = 'none';
    }

    function hideError() {
        errorBox.style.display = 'none';
    }

    function fetchVideoInfo(url) {
        hideError();
        fetchBtn.disabled = true;
        fetchBtn.innerHTML = '<span class="spinner"></span> <span>Fetching...</span>';
        metadataContainer.style.display = 'none';
        progressContainer.style.display = 'none';
        if (skeletonLoader) skeletonLoader.style.display = 'block';

        fetch('/api/info', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => { throw new Error(data.error || "Failed to fetch metadata") });
            }
            return response.json();
        })
        .then(data => {
            renderMetadata(data);
        })
        .catch(err => {
            showError(err.message);
        })
        .finally(() => {
            fetchBtn.disabled = false;
            fetchBtn.innerHTML = '<span>Fetch Details</span> <i class="fa-solid fa-arrow-right"></i>';
            if (skeletonLoader) skeletonLoader.style.display = 'none';
        });
    }

    function renderMetadata(data) {
        metadataContainer.innerHTML = '';
        
        if (data.is_playlist) {
            // Render Playlist Template
            metadataContainer.innerHTML = `
                <div class="metadata-card fade-in">
                    <div class="thumbnail-wrapper">
                        <img src="${data.thumbnail || 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=300&auto=format&fit=crop'}" class="thumbnail-img" alt="playlist thumbnail">
                        <span class="duration-badge">${data.total_videos} Videos</span>
                    </div>
                    <div class="video-details">
                        <div>
                            <h3 class="video-title">${data.title}</h3>
                            <p class="channel-name"><i class="fa-solid fa-folder-open"></i> Channel: ${data.channel}</p>
                        </div>
                        <div class="download-options">
                            <p style="font-size: 13px; color: var(--text-secondary);">Select download quality for videos:</p>
                            <div class="option-group">
                                <select id="playlistQuality" class="select-control">
                                    <option value="1080">1080p (Full HD)</option>
                                    <option value="720" selected>720p (HD)</option>
                                    <option value="480">480p (SD)</option>
                                    <option value="360">360p (Low)</option>
                                </select>
                                <label class="checkbox-label" style="margin-top: 10px;">
                                    <input type="checkbox" id="playlistAudioOnly"> Audio Only (MP3)
                                </label>
                            </div>
                            <div class="action-row">
                                <button id="downloadPlaylistBtn" class="search-btn" style="flex: 1;"><i class="fa-solid fa-download"></i> Download First Video</button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <h4 style="margin-top: 30px; margin-bottom: 15px; font-size: 16px; text-align: left; font-family: 'Outfit';">Playlist Tracks</h4>
                <div class="item-list" style="max-height: 250px; overflow-y: auto; border: 1px solid var(--card-border); padding: 10px; border-radius: 12px; background: var(--input-bg);">
                    ${data.videos.map((vid, idx) => `
                        <div style="display:flex; justify-content:space-between; align-items:center; padding: 10px 5px; border-bottom: 1px solid var(--card-border);">
                            <span style="font-size:13px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap; max-width:75%; text-align: left;">${idx+1}. ${vid.title}</span>
                            <div style="display: flex; gap: 8px; align-items: center;">
                                <span style="font-size: 11px; color: var(--text-secondary);"><i class="fa-regular fa-clock"></i> ${vid.duration}</span>
                                <button onclick="document.getElementById('videoUrl').value='${vid.url}'; document.getElementById('fetchBtn').click();" class="nav-btn nav-btn-outline" style="padding: 4px 8px; font-size: 11px; cursor: pointer;">Load</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            
            document.getElementById('downloadPlaylistBtn').addEventListener('click', () => {
                showToast("Downloading playlist videos sequentially in the background.", "success");
                if (data.videos.length > 0) {
                    const qual = document.getElementById('playlistQuality').value;
                    const audio = document.getElementById('playlistAudioOnly').checked;
                    triggerDownload(data.videos[0].url, qual, audio, false);
                }
            });
            
        } else {
            // Render Single Video Template with expanded metadata (views, likes, date)
            metadataContainer.innerHTML = `
                <div class="metadata-card fade-in">
                    <div class="thumbnail-wrapper">
                        <img src="${data.thumbnail || 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=300&auto=format&fit=crop'}" class="thumbnail-img" alt="video thumbnail">
                        <span class="duration-badge">${data.duration}</span>
                    </div>
                    <div class="video-details">
                        <div>
                            <h3 class="video-title" id="metadataTitle">${data.title}</h3>
                            <p class="channel-name" id="metadataChannel" style="margin-bottom: 8px;"><i class="fa-solid fa-circle-user"></i> ${data.channel}</p>
                            
                            <!-- Video Specs Row -->
                            <div style="display: flex; gap: 15px; font-size: 12px; color: var(--text-secondary); margin-bottom: 20px; flex-wrap: wrap;">
                                <span><i class="fa-solid fa-eye"></i> ${data.view_count} views</span>
                                <span><i class="fa-solid fa-thumbs-up"></i> ${data.like_count} likes</span>
                                <span><i class="fa-solid fa-calendar-day"></i> ${data.upload_date}</span>
                            </div>
                        </div>
                        <div class="download-options">
                            <div class="option-group">
                                <select id="downloadQuality" class="select-control">
                                    ${data.qualities.map(q => `<option value="${q.height}">${q.resolution} | ${q.codec} | ${q.fps} | ${q.estimated_size}</option>`).join('')}
                                    <option value="audio">Audio Only | MP3 | 192kbps | ${data.audio_size}</option>
                                </select>
                                <div style="display:flex; flex-direction:column; gap:8px;">
                                    <label class="checkbox-label" style="user-select:none;">
                                        <input type="checkbox" id="downloadSubtitles"> Subtitles (EN)
                                    </label>
                                    <label class="checkbox-label" id="favLabel" style="color: var(--primary); font-weight:600; cursor: pointer; user-select:none;">
                                        <span id="favHeartBtn"><i class="fa-regular fa-heart"></i> Add Favorite</span>
                                    </label>
                                </div>
                            </div>
                            <div class="action-row">
                                <button id="downloadBtn" class="search-btn" style="flex: 2;"><i class="fa-solid fa-download"></i> Start Download</button>
                                <button id="copyInfoBtn" class="search-btn btn-secondary" style="flex: 1;"><i class="fa-solid fa-copy"></i> Copy Info</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Handle Download Button
            document.getElementById('downloadBtn').addEventListener('click', () => {
                const qualSelect = document.getElementById('downloadQuality').value;
                const audioOnly = qualSelect === 'audio';
                const quality = audioOnly ? '720' : qualSelect;
                const subtitle = document.getElementById('downloadSubtitles').checked;
                
                triggerDownload(data.url, quality, audioOnly, subtitle);
            });
            
            // Copy Info Button
            document.getElementById('copyInfoBtn').addEventListener('click', () => {
                const text = `Title: ${data.title}\nChannel: ${data.channel}\nDuration: ${data.duration}\nURL: ${data.url}\nViews: ${data.view_count}\nLikes: ${data.like_count}\nUploaded: ${data.upload_date}`;
                navigator.clipboard.writeText(text)
                    .then(() => showToast("Copied video details to clipboard!", "success"))
                    .catch(err => console.error("Clipboard copy failed:", err));
            });
            
            // Add Favorite Button
            const favBtn = document.getElementById('favHeartBtn');
            favBtn.addEventListener('click', () => {
                fetch('/api/favorites', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        url: data.url,
                        title: data.title,
                        thumbnail: data.thumbnail,
                        channel: data.channel,
                        duration: data.duration
                    })
                })
                .then(res => {
                    if (res.status === 401) {
                        showToast("Please login to save favorites.", "error");
                        return;
                    }
                    return res.json();
                })
                .then(resData => {
                    if (resData && resData.message) {
                        favBtn.innerHTML = '<i class="fa-solid fa-heart"></i> Saved!';
                        showToast("Added to favorites!", "success");
                    }
                })
                .catch(err => console.error(err));
            });
        }

        metadataContainer.style.display = 'block';
    }

    function triggerDownload(url, quality, audioOnly, subtitle) {
        showToast("Adding job to download queue...", "info");
        
        fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                quality: quality,
                audio_only: audioOnly,
                subtitle: subtitle
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => { throw new Error(data.error || "Failed to start download") });
            }
            return response.json();
        })
        .then(data => {
            showToast("Job added to queue! Check status below.", "success");
            // Highlight queue section and force a poll
            if (queueSection) queueSection.style.display = 'block';
            pollQueueStatus();
        })
        .catch(err => {
            showToast(err.message, "error");
        });
    }

    // ── 7. Queue Polling & Managing ──────────────────────────────────────────
    function startQueuePolling() {
        // Poll every 1.5 seconds
        setInterval(pollQueueStatus, 1500);
    }

    function pollQueueStatus() {
        if (!queueList) return;
        
        fetch('/api/queue')
        .then(res => res.json())
        .then(tasks => {
            if (tasks.length === 0) {
                if (queueSection) queueSection.style.display = 'none';
                if (progressContainer) progressContainer.style.display = 'none';
                return;
            }
            
            // Update the main progress card if there is an active downloading task
            const activeTask = tasks.find(t => t.status === 'downloading');
            if (activeTask && progressContainer) {
                progressContainer.style.display = 'block';
                const pTitle = document.getElementById('progressTitle');
                const pPercent = document.getElementById('progressPercent');
                const pBarFill = document.getElementById('progressBarFill');
                const pSpeed = document.getElementById('progressSpeed');
                const pSizes = document.getElementById('progressSizes');
                const pEta = document.getElementById('progressEta');
                
                if (pTitle) pTitle.innerText = `Downloading: ${activeTask.title}`;
                const pctVal = Math.round(activeTask.percent || 0);
                if (pPercent) pPercent.innerText = `${pctVal}%`;
                if (pBarFill) pBarFill.style.width = `${pctVal}%`;
                
                let sizeLbl = "-- / -- MB";
                if (activeTask.downloaded_size_mb && activeTask.total_size_mb) {
                    sizeLbl = `${activeTask.downloaded_size_mb} MB / ${activeTask.total_size_mb} MB`;
                } else if (activeTask.downloaded_size_mb) {
                    sizeLbl = `${activeTask.downloaded_size_mb} MB`;
                }
                
                if (pSpeed) pSpeed.innerHTML = `<i class="fa-solid fa-gauge-high"></i> Speed: ${activeTask.speed || 'N/A'}`;
                if (pSizes) pSizes.innerText = sizeLbl;
                if (pEta) pEta.innerHTML = `<i class="fa-solid fa-clock"></i> ETA: ${activeTask.eta || 'N/A'}`;
            } else {
                if (progressContainer) progressContainer.style.display = 'none';
            }
            
            if (queueSection) queueSection.style.display = 'block';
            
            queueList.innerHTML = '';
            
            tasks.forEach(task => {
                // If a task completes, trigger automated file download and notify
                if (task.status === 'completed' && !completedTasks.has(task.id)) {
                    completedTasks.add(task.id);
                    
                    // Trigger toast notification
                    showToast(`Download finished: "${task.title}"`, "success");
                    
                    // Show success completion modal or summary summary
                    renderSummaryAlert(task);
                    
                    // Trigger actual file download in browser using window.location.origin to prevent mixed content/insecure errors
                    const dlUrl = `${window.location.origin}/file/${encodeURIComponent(task.filename)}`;
                    
                    // Fetch the file as a blob to bypass "insecure download" warnings on HTTP connections
                    fetch(dlUrl)
                        .then(response => {
                            if (!response.ok) throw new Error("Failed to download file from server");
                            return response.blob();
                        })
                        .then(blob => {
                            const blobUrl = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = blobUrl;
                            a.download = task.filename;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            // Clean up the object URL after a short delay
                            setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1000);
                        })
                        .catch(err => {
                            console.error("Blob download failed, falling back to direct link:", err);
                            const a = document.createElement('a');
                            a.href = dlUrl;
                            a.download = task.filename;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                        });
                }
                
                // Render queue list item
                let percentage = Math.round(task.percent || 0);
                let speedLbl = task.speed || 'N/A';
                let etaLbl = task.eta || 'N/A';
                
                let sizeLbl = "";
                if (task.downloaded_size_mb && task.total_size_mb) {
                    sizeLbl = `${task.downloaded_size_mb} MB / ${task.total_size_mb} MB`;
                } else if (task.downloaded_size_mb) {
                    sizeLbl = `${task.downloaded_size_mb} MB`;
                }
                
                let badgeClass = 'badge-info';
                if (task.status === 'completed') badgeClass = 'badge-success';
                else if (task.status === 'failed') badgeClass = 'badge-danger';
                else if (task.status === 'paused') badgeClass = 'badge-warning';
                else if (task.status === 'cancelled') badgeClass = 'badge-secondary';
                else if (task.status === 'downloading') badgeClass = 'badge-primary';
                
                let controlsHtml = '';
                if (task.status === 'downloading' || task.status === 'queued') {
                    controlsHtml = `
                        <button onclick="controlQueueTask('${task.id}', 'pause')" class="ctrl-btn" title="Pause"><i class="fa-solid fa-pause"></i></button>
                        <button onclick="controlQueueTask('${task.id}', 'cancel')" class="ctrl-btn ctrl-btn-danger" title="Cancel"><i class="fa-solid fa-xmark"></i></button>
                    `;
                } else if (task.status === 'paused') {
                    controlsHtml = `
                        <button onclick="controlQueueTask('${task.id}', 'resume')" class="ctrl-btn ctrl-btn-success" title="Resume"><i class="fa-solid fa-play"></i></button>
                        <button onclick="controlQueueTask('${task.id}', 'cancel')" class="ctrl-btn ctrl-btn-danger" title="Cancel"><i class="fa-solid fa-xmark"></i></button>
                    `;
                } else if (task.status === 'completed') {
                    controlsHtml = `
                        <a href="${window.location.origin}/file/${encodeURIComponent(task.filename)}" download class="ctrl-btn ctrl-btn-success" title="Save to Device" style="display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; text-decoration: none;"><i class="fa-solid fa-download"></i></a>
                        <button onclick="controlQueueTask('${task.id}', 'remove')" class="ctrl-btn ctrl-btn-danger" title="Remove From List"><i class="fa-solid fa-trash"></i></button>
                    `;
                } else if (task.status === 'failed' || task.status === 'cancelled') {
                    controlsHtml = `
                        <button onclick="controlQueueTask('${task.id}', 'retry')" class="ctrl-btn ctrl-btn-success" title="Retry Download"><i class="fa-solid fa-rotate-left"></i></button>
                        <button onclick="controlQueueTask('${task.id}', 'remove')" class="ctrl-btn ctrl-btn-danger" title="Remove From List"><i class="fa-solid fa-trash"></i></button>
                    `;
                }

                queueList.innerHTML += `
                    <div class="queue-item card-hover">
                        <div style="flex:1; min-width:0; text-align: left;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                <h4 class="queue-title" title="${task.title}">${task.title}</h4>
                                <span class="badge ${badgeClass}">${task.status.toUpperCase()}</span>
                            </div>
                            
                            ${task.status === 'downloading' ? `
                                <div class="bar-container" style="margin-bottom:8px;">
                                    <div class="bar-fill" style="width: ${percentage}%;"></div>
                                </div>
                                <div class="progress-footer" style="font-size:11px;">
                                    <span><i class="fa-solid fa-gauge-high"></i> ${speedLbl}</span>
                                    <span>${sizeLbl} (${percentage}%)</span>
                                    <span><i class="fa-solid fa-clock"></i> ETA: ${etaLbl}</span>
                                </div>
                            ` : `
                                <div style="font-size:12px; color: var(--text-secondary);">
                                    ${task.error ? `<span style="color:var(--danger);"><i class="fa-solid fa-circle-exclamation"></i> Error: ${task.error}</span>` : `Status: ${task.status}`}
                                </div>
                            `}
                        </div>
                        <div class="queue-controls" style="margin-left: 15px; display: flex; gap: 8px;">
                            ${controlsHtml}
                        </div>
                    </div>
                `;
            });
        })
        .catch(err => console.error("Error fetching queue details:", err));
    }

    // Direct helper mapping control actions to backend API blueprints
    window.controlQueueTask = function(taskId, action) {
        fetch(`/api/queue/${action}/${taskId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, "error");
            } else {
                showToast(data.message, "success");
                pollQueueStatus();
            }
        })
        .catch(err => console.error(`Error performing ${action} on task:`, err));
    }

    function renderSummaryAlert(task) {
        // Render a beautiful download summary alert at the top of the body
        const summaryDiv = document.createElement('div');
        summaryDiv.style.position = 'fixed';
        summaryDiv.style.top = '10%';
        summaryDiv.style.left = '50%';
        summaryDiv.style.transform = 'translate(-50%, -10%)';
        summaryDiv.style.zIndex = '9999';
        summaryDiv.innerHTML = `
            <div class="glass-card success-animation" style="max-width: 450px; border: 1px solid var(--success); text-align: center; box-shadow: 0 10px 40px var(--success-glow);">
                <div style="font-size: 48px; color: var(--success); margin-bottom: 15px;"><i class="fa-solid fa-circle-check"></i></div>
                <h3 style="font-family: 'Outfit'; font-size: 20px; margin-bottom: 10px;">Download Successful!</h3>
                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">"${task.title}"</p>
                <div style="background: var(--input-bg); border-radius: 10px; padding: 12px; font-size: 12px; display: flex; justify-content: space-around; margin-bottom: 20px;">
                    <div><strong>File Size:</strong><br>${task.total_size_mb || task.file_size_mb || 'N/A'} MB</div>
                    <div><strong>Status:</strong><br><span style="color:var(--success);">Completed</span></div>
                    <div><strong>Saved:</strong><br>Downloads Folder</div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <a href="${window.location.origin}/file/${encodeURIComponent(task.filename)}" download class="nav-btn nav-btn-primary" style="border: none; padding: 8px 25px; cursor: pointer; flex: 1; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; font-size: 14px;"><i class="fa-solid fa-download" style="margin-right: 8px;"></i> Save File</a>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" class="nav-btn nav-btn-outline" style="padding: 8px 25px; cursor: pointer; flex: 1; font-size: 14px;">Dismiss</button>
                </div>
            </div>
        `;
        document.body.appendChild(summaryDiv);
        
        // Auto-remove alert after 7 seconds
        setTimeout(() => {
            if (summaryDiv.parentElement) {
                summaryDiv.remove();
            }
        }, 7000);
    }

    function showToast(message, type = "success") {
        const toastContainer = document.getElementById('toastContainer') || document.body;
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : (type === 'info' ? 'fa-circle-info' : 'fa-circle-exclamation')}"></i>
            <span>${message}</span>
        `;
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            setTimeout(() => toast.remove(), 500);
        }, 4000);
    }
});
