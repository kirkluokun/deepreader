/**
 * DeepReader 前端应用逻辑
 * 处理文件上传、WebSocket通信、进度显示和结果渲染
 */

class DeepReaderApp {
    constructor() {
        this.websocket = null;
        this.taskId = null;
        this.currentFile = null;
        
        this.initializeElements();
        this.setupEventListeners();
        this.setupDropZone();
    }

    initializeElements() {
        // 表单元素
        this.fileInput = document.getElementById('fileInput');
        this.dropZone = document.getElementById('dropZone');
        this.selectedFile = document.getElementById('selectedFile');
        this.fileName = document.getElementById('fileName');
        this.coreQuestion = document.getElementById('coreQuestion');
        this.researchRole = document.getElementById('researchRole');
        this.customRole = document.getElementById('customRole');
        this.uploadForm = document.getElementById('uploadForm');
        this.startBtn = document.getElementById('startBtn');

        // 进度元素
        this.inputSection = document.getElementById('inputSection');
        this.progressSection = document.getElementById('progressSection');
        this.progressBar = document.getElementById('progressBar');
        this.progressText = document.getElementById('progressText');
        this.progressPercent = document.getElementById('progressPercent');
        this.logContainer = document.getElementById('logContainer');

        // 节点状态元素
        this.nodeRag = document.getElementById('node-rag');
        this.nodeReading = document.getElementById('node-reading');
        this.nodeReport = document.getElementById('node-report');

        // 结果元素
        this.resultsSection = document.getElementById('resultsSection');
        this.tabButtons = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');
    }

    setupEventListeners() {
        // 文件选择
        this.fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });

        // 研究角色选择
        this.researchRole.addEventListener('change', (e) => {
            if (e.target.value === '自定义') {
                this.customRole.classList.remove('hidden');
                this.customRole.focus();
            } else {
                this.customRole.classList.add('hidden');
            }
        });

        // 表单提交
        this.uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.startAnalysis();
        });

        // 标签页切换
        this.tabButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
    }

    setupDropZone() {
        // 拖拽上传
        this.dropZone.addEventListener('click', () => {
            this.fileInput.click();
        });

        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('border-blue-400');
        });

        this.dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('border-blue-400');
        });

        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('border-blue-400');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        });
    }

    handleFileSelect(file) {
        if (!file) return;

        // 检查文件类型
        const allowedTypes = ['application/pdf', 'application/epub+zip', 'text/markdown'];
        const allowedExtensions = ['.pdf', '.epub', '.md'];
        
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!allowedExtensions.includes(fileExtension)) {
            this.showError('不支持的文件类型。请上传 PDF、EPUB 或 Markdown 文件。');
            return;
        }

        this.currentFile = file;
        this.fileName.textContent = file.name;
        this.selectedFile.classList.remove('hidden');

        // 隐藏拖拽区域的内容
        this.dropZone.querySelector('svg').style.display = 'none';
        this.dropZone.querySelector('p').style.display = 'none';
        this.dropZone.querySelector('.text-xs').style.display = 'none';
    }

    async startAnalysis() {
        if (!this.currentFile) {
            this.showError('请选择要分析的文档文件。');
            return;
        }

        if (!this.coreQuestion.value.trim()) {
            this.showError('请输入核心探索问题。');
            return;
        }

        this.startBtn.disabled = true;
        this.startBtn.textContent = '正在上传...';

        try {
            // 1. 上传文件
            const uploadResult = await this.uploadFile();
            if (!uploadResult.success) {
                throw new Error(uploadResult.error);
            }

            // 2. 获取研究角色
            const role = this.researchRole.value === '自定义' 
                ? this.customRole.value.trim() 
                : this.researchRole.value;

            if (!role) {
                throw new Error('请输入研究身份。');
            }

            // 3. 开始研究任务
            const researchResult = await this.startResearchTask(
                uploadResult.filename,
                this.coreQuestion.value.trim(),
                role
            );

            if (!researchResult.success) {
                throw new Error(researchResult.error);
            }

            // 4. 建立WebSocket连接
            this.taskId = researchResult.task_id;
            this.connectWebSocket();

            // 5. 显示进度界面
            this.showProgressSection();

        } catch (error) {
            this.showError(error.message);
            this.resetStartButton();
        }
    }

    async uploadFile() {
        const formData = new FormData();
        formData.append('file', this.currentFile);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok) {
                return { success: true, filename: result.filename };
            } else {
                return { success: false, error: result.detail || '文件上传失败' };
            }
        } catch (error) {
            return { success: false, error: '网络错误：' + error.message };
        }
    }

    async startResearchTask(filename, question, role) {
        const formData = new FormData();
        formData.append('filename', filename);
        formData.append('user_core_question', question);
        formData.append('research_role', role);

        try {
            const response = await fetch('/api/start_research', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok) {
                return { success: true, task_id: result.task_id };
            } else {
                return { success: false, error: result.detail || '启动研究任务失败' };
            }
        } catch (error) {
            return { success: false, error: '网络错误：' + error.message };
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${this.taskId}`;
        
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            this.addLog('WebSocket连接已建立', 'info');
        };

        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('解析WebSocket消息失败:', error);
            }
        };

        this.websocket.onerror = (error) => {
            this.addLog('WebSocket连接错误', 'error');
            console.error('WebSocket error:', error);
        };

        this.websocket.onclose = () => {
            this.addLog('WebSocket连接已关闭', 'info');
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'progress':
                this.updateProgress(data.progress, data.message);
                this.updateNodeStatus(data.stage);
                this.addLog(`${data.message} (${data.progress}%)`, 'info');
                break;

            case 'node_update':
                this.handleNodeUpdate(data.event);
                break;

            case 'completion':
                this.handleCompletion(data);
                break;

            case 'error':
                this.handleError(data.message);
                break;

            default:
                console.log('未知消息类型:', data);
        }
    }

    updateProgress(progress, message) {
        this.progressBar.style.width = `${progress}%`;
        this.progressPercent.textContent = `${progress}%`;
        this.progressText.textContent = message;
    }

    updateNodeStatus(stage) {
        // 重置所有节点状态
        [this.nodeRag, this.nodeReading, this.nodeReport].forEach(node => {
            const indicator = node.querySelector('.w-3');
            indicator.className = 'w-3 h-3 bg-gray-300 rounded-full mr-3';
            node.classList.remove('node-animation');
        });

        // 更新当前活动节点
        let activeNode;
        switch (stage) {
            case 'rag_preparation':
            case 'rag_parsing':
                activeNode = this.nodeRag;
                break;
            case 'reading':
                activeNode = this.nodeReading;
                break;
            case 'report_generation':
                activeNode = this.nodeReport;
                break;
        }

        if (activeNode) {
            const indicator = activeNode.querySelector('.w-3');
            indicator.className = 'w-3 h-3 bg-blue-500 rounded-full mr-3';
            activeNode.classList.add('node-animation');
        }
    }

    handleNodeUpdate(event) {
        for (const [nodeName, nodeData] of Object.entries(event)) {
            this.addLog(`节点 ${nodeName} 更新`, 'debug');
        }
    }

    handleCompletion(data) {
        this.updateProgress(100, '分析完成！');
        this.addLog('分析完成，正在加载结果...', 'success');
        
        // 显示结果
        if (data.final_state) {
            this.displayResults(data.final_state);
        }

        // 标记所有节点为完成状态
        [this.nodeRag, this.nodeReading, this.nodeReport].forEach(node => {
            const indicator = node.querySelector('.w-3');
            indicator.className = 'w-3 h-3 bg-green-500 rounded-full mr-3';
            node.classList.remove('node-animation');
        });
    }

    handleError(message) {
        this.addLog(`错误: ${message}`, 'error');
        this.showError(message);
        this.resetStartButton();
    }

    displayResults(finalState) {
        // 格式化和显示各种报告
        if (finalState.draft_report) {
            this.renderMarkdown('draft-report', this.formatDraftReport(finalState.draft_report));
        }

        if (finalState.chapter_summaries) {
            this.renderMarkdown('chapter-summary', this.formatChapterSummaries(finalState.chapter_summaries));
        }

        if (finalState.thematic_analysis) {
            this.renderMarkdown('thematic-analysis', this.formatThematicAnalysis(finalState.thematic_analysis));
        }

        if (finalState.raw_reviewer_outputs) {
            this.renderMarkdown('debate-questions', this.formatDebateQuestions(finalState.raw_reviewer_outputs));
        }

        this.resultsSection.classList.remove('hidden');
    }

    formatDraftReport(reportData) {
        if (!reportData || !Array.isArray(reportData)) {
            return "未能生成最终报告。";
        }

        let md = "";

        function parseRecursive(sections, level) {
            for (const section of sections) {
                const title = section.title || "无标题";
                md += `${"#".repeat(level)} ${title}\n\n`;

                if (section.content_brief) {
                    md += `_${section.content_brief}_\n\n`;
                }

                if (section.written_content && Array.isArray(section.written_content)) {
                    md += section.written_content.join("\n\n") + "\n\n";
                }

                if (section.children && Array.isArray(section.children)) {
                    parseRecursive(section.children, level + 1);
                }
            }
        }

        parseRecursive(reportData, 1);
        return md;
    }

    formatChapterSummaries(summaries) {
        if (!summaries || typeof summaries !== 'object') {
            return "没有可用的章节摘要。";
        }

        let md = "# 章节摘要\n\n";
        for (const [title, summary] of Object.entries(summaries)) {
            md += `## ${title}\n\n${summary}\n\n`;
        }
        return md;
    }

    formatThematicAnalysis(analysis) {
        if (!analysis || typeof analysis !== 'object') {
            return "没有可用的主题分析。";
        }

        let md = "# 主题思想分析\n\n";
        for (const [key, value] of Object.entries(analysis)) {
            const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            md += `## ${formattedKey}\n\n${value}\n\n`;
        }
        return md;
    }

    formatDebateQuestions(rounds) {
        if (!rounds || !Array.isArray(rounds)) {
            return "没有可用的辩论记录。";
        }

        let md = "# 批判性辩论问答\n\n";
        rounds.forEach((roundData, i) => {
            md += `## 辩论轮次 ${i + 1}\n\n`;
            if (Array.isArray(roundData)) {
                roundData.forEach(item => {
                    const question = item.question || 'N/A';
                    const answer = item.content_retrieve_answer || '无回答';
                    md += `### 问题: ${question}\n\n**回答:** ${answer}\n\n`;
                });
            }
        });
        return md;
    }

    renderMarkdown(containerId, content) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = marked.parse(content);
            // 代码高亮
            Prism.highlightAllUnder(container);
        }
    }

    switchTab(tabId) {
        // 更新标签按钮状态
        this.tabButtons.forEach(btn => {
            if (btn.dataset.tab === tabId) {
                btn.classList.add('active', 'border-blue-500', 'text-blue-600');
                btn.classList.remove('border-transparent', 'text-gray-500');
            } else {
                btn.classList.remove('active', 'border-blue-500', 'text-blue-600');
                btn.classList.add('border-transparent', 'text-gray-500');
            }
        });

        // 更新内容显示
        this.tabContents.forEach(content => {
            if (content.id === tabId) {
                content.classList.remove('hidden');
            } else {
                content.classList.add('hidden');
            }
        });
    }

    showProgressSection() {
        this.inputSection.style.display = 'none';
        this.progressSection.classList.remove('hidden');
    }

    addLog(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const colors = {
            info: 'text-blue-400',
            success: 'text-green-400',
            error: 'text-red-400',
            debug: 'text-gray-400'
        };

        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${colors[type] || colors.info}`;
        logEntry.innerHTML = `<span class="text-gray-500">[${timestamp}]</span> ${message}`;

        this.logContainer.appendChild(logEntry);
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }

    showError(message) {
        alert(`错误: ${message}`);
    }

    resetStartButton() {
        this.startBtn.disabled = false;
        this.startBtn.textContent = '🚀 开始深度分析';
    }
}

// 配置marked选项
marked.setOptions({
    breaks: true,
    gfm: true,
    sanitize: false
});

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new DeepReaderApp();
});