document.addEventListener('DOMContentLoaded', () => {
    const apiStatus = document.getElementById('api-status');
    const clinicSelect = document.getElementById('clinic-select');
    const docTypeSelect = document.getElementById('doc-type-select');
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    
    // Status initialization
    checkStatus();
    loadOptions();

    async function checkStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if(data.authenticated) {
                apiStatus.textContent = 'API Connected';
                apiStatus.className = 'status-badge connected';
            } else {
                apiStatus.textContent = 'Auth Failed';
                apiStatus.className = 'status-badge error';
            }
        } catch(e) {
            apiStatus.textContent = 'Offline';
            apiStatus.className = 'status-badge error';
        }
    }

    async function loadOptions() {
        try {
            // Document types
            const docsRes = await fetch('/api/document_types');
            const docs = await docsRes.json();
            docTypeSelect.innerHTML = docs.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
            docTypeSelect.disabled = false;
            
            // Prefer "RemissBot", then "Inreferral", or "Remiss"
            const remissBot = docs.find(d => d.name.toLowerCase() === 'remissbot');
            const inreferral = docs.find(d => d.name.toLowerCase().includes('inreferral') || d.name.toLowerCase().includes('remiss'));
            if(remissBot) docTypeSelect.value = remissBot.id;
            else if(inreferral) docTypeSelect.value = inreferral.id;
            
            // Clinics
            const clinicsRes = await fetch('/api/clinics');
            const clinics = await clinicsRes.json();
            clinicSelect.innerHTML = clinics.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
            clinicSelect.disabled = false;
        } catch(e) {
            console.error("Failed to load options");
        }
    }

    // Drag and drop setup
    dropZone.addEventListener('click', () => fileInput.click());
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function getBasePN(filename) {
        const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.')) || filename;
        let match = nameWithoutExt.match(/((?:19|20)\d{6})[-+]?(\d{4})/);
        if(match) return `${match[1]}-${match[2]}`;
        match = nameWithoutExt.match(/(\d{6})[-+]?(\d{4})/);
        if(match) {
            let century = parseInt(match[1].substring(0, 2)) > 30 ? "19" : "20";
            return `${century}${match[1]}-${match[2]}`;
        }
        return nameWithoutExt;
    }

    async function handleFiles(files) {
        if(!files.length) return;
        
        const clinicId = clinicSelect.value;
        const docTypeId = docTypeSelect.value;
        
        if(!clinicId || !docTypeId) {
            alert("Please wait for configurations to load");
            return;
        }

        const panel = document.getElementById('results-panel');
        const fileList = document.getElementById('file-list');
        panel.style.display = 'block';
        
        const baseInputEl = document.getElementById('base-personnummer');
        const forcedBase = baseInputEl ? baseInputEl.value.trim() : "";

        // Group files
        const groupedFiles = {};
        Array.from(files).forEach(file => {
            const base = forcedBase ? forcedBase : getBasePN(file.name);
            if (!groupedFiles[base]) groupedFiles[base] = [];
            groupedFiles[base].push(file);
        });

        const groups = Object.keys(groupedFiles).map(base => {
            // Sort files alphabetically to ensure base, A, B, C order
            const groupFiles = groupedFiles[base].sort((a, b) => a.name.localeCompare(b.name));
            return { base, files: groupFiles };
        });

        let stats = { total: groups.length, success: 0, failed: 0 };
        updateStats(stats);
        
        const items = groups.map(group => {
            const li = document.createElement('li');
            li.className = 'file-item';
            const fileNames = group.files.map(f => f.name).join(', ');
            li.innerHTML = `
                <div class="file-item-info">
                    <strong>${group.files.length > 1 ? 'Group: ' : ''}${fileNames}</strong>
                    <span class="text-xs">Processing ${group.files.length} file(s)...</span>
                </div>
                <div class="file-item-status text-pending">Pending</div>
            `;
            fileList.prepend(li);
            return { group, li };
        });

        for(let i=0; i<items.length; i++) {
            const { group, li } = items[i];
            const formData = new FormData();
            
            group.files.forEach(f => {
                formData.append('file', f);
            });
            
            formData.append('clinicId', clinicId);
            formData.append('documentTypeId', docTypeId);
            // Append base personnummer hint
            formData.append('basePersonnummer', group.base);
            
            try {
                const res = await fetch('/api/upload_group', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                
                if(data.success) {
                    stats.success++;
                    li.querySelector('.file-item-status').className = 'file-item-status text-success';
                    li.querySelector('.file-item-status').textContent = 'Uploaded';
                    li.querySelector('.text-xs').textContent = `Patient: ${data.patient.name} (${data.patient.pn})`;
                } else {
                    stats.failed++;
                    li.querySelector('.file-item-status').className = 'file-item-status text-error';
                    li.querySelector('.file-item-status').textContent = 'Failed';
                    li.querySelector('.text-xs').textContent = data.message;
                }
            } catch(e) {
                stats.failed++;
                li.querySelector('.file-item-status').className = 'file-item-status text-error';
                li.querySelector('.file-item-status').textContent = 'Failed';
                li.querySelector('.text-xs').textContent = 'Network error';
            }
            
            updateStats(stats, ((i+1)/groups.length)*100);
        }
    }
    
    function updateStats(stats, progress) {
        document.getElementById('stat-total').textContent = `Total: ${stats.total}`;
        document.getElementById('stat-success').textContent = `Success: ${stats.success}`;
        document.getElementById('stat-failed').textContent = `Failed: ${stats.failed}`;
        if(progress !== undefined) {
            document.getElementById('progress-bar').style.width = `${progress}%`;
        }
    }
});
