// Alert 系統
function showAlert(message, type = 'success') {
    const alertContainer = document.getElementById('alertContainer');
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // 3秒後自動移除
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 1500);
 }
 
 // 驗證系統
 class VerificationSystem {
    constructor() {
        this.isVerified = false;
        this.timerId = null;
        console.log('VerificationSystem 已初始化');
    }
 
    async sendVerificationCode(email) {
        try {
            console.log('開始發送驗證碼到:', email);
            const response = await fetch('/send-verify-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: email })
            });
 
            console.log('收到服務器回應:', response);
            const data = await response.json();
            console.log('回應數據:', data);
            
            if (response.ok) {
                console.log('驗證碼發送成功');
                showAlert('驗證碼已發送到您的信箱', 'success');
                return true;
            } else {
                console.log('驗證碼發送失敗:', data.error);
                showAlert(data.error || '發送驗證碼失敗', 'danger');
                return false;
            }
        } catch (error) {
            console.error('發送驗證碼錯誤:', error);
            showAlert('發送驗證碼時發生錯誤', 'danger');
            return false;
        }
    }
 
    async verifyCode(email, code) {
        try {
            console.log('開始驗證碼驗證, email:', email, 'code:', code);
            const response = await fetch('/verify-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    email: email,
                    code: code 
                })
            });
 
            console.log('收到驗證回應:', response);
            const data = await response.json();
            console.log('驗證回應數據:', data);
            
            if (response.ok) {
                console.log('驗證成功');
                showAlert('驗證成功', 'success');
                return true;
            } else {
                console.log('驗證失敗:', data.error);
                showAlert(data.error || '驗證碼錯誤', 'danger');
                return false;
            }
        } catch (error) {
            console.error('驗證過程錯誤:', error);
            showAlert('驗證時發生錯誤', 'danger');
            return false;
        }
    }
 
    startTimer(onExpire) {
        let timeLeft = 300; // 5分鐘倒計時
        const timerDisplay = document.getElementById('timer');
        console.log('開始計時器');
        
        this.timerId = setInterval(() => {
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            timerDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            if (timeLeft <= 0) {
                console.log('計時器結束');
                clearInterval(this.timerId);
                if (onExpire) onExpire();
            }
            timeLeft--;
        }, 1000);
    }
 }
 
// 註冊系統
 class RegisterSystem {
    static init() {
        console.log('RegSystem init start');
        
        // 檢查所有必要元素
        const elements = {
            sendVerifyBtn: document.getElementById('sendVerifyBtn'),
            email: document.getElementById('email'),
            verifyCodeInput: document.getElementById('verifyCode'),
            verifyCodeGroup: document.getElementById('verifyCodeGroup'),
            registerBtn: document.getElementById('registerBtn'),
            timer: document.getElementById('timer')
        };
 
        // 檢查元素是否都存在
        for (const [key, element] of Object.entries(elements)) {
            console.log(`元素 ${key}:`, element);
            if (!element) {
                console.log(`找不到${key}元素`);
                return;
            }
        }
 
        const verificationSystem = new VerificationSystem();
        
        // 綁定發送驗證碼事件
        elements.sendVerifyBtn.onclick = async (e) => {
            console.log('Send verify button clicked');
            e.preventDefault();
            
            const email = elements.email.value.trim();
            console.log('Email:', email);
 
            if (!email) {
                showAlert('請輸入電子信箱', 'warning');
                return;
            }
 
            try {
                elements.sendVerifyBtn.disabled = true;
                elements.sendVerifyBtn.textContent = '發送中...';
                
                if (await verificationSystem.sendVerificationCode(email)) {
                    elements.verifyCodeGroup.style.display = 'block';
                    elements.email.readOnly = true;
                    
                    verificationSystem.startTimer(() => {
                        elements.sendVerifyBtn.disabled = false;
                        elements.sendVerifyBtn.textContent = '發送驗證碼';
                        elements.email.readOnly = false;
                        elements.timer.textContent = '驗證碼已過期';
                        elements.verifyCodeInput.value = '';
                        elements.verifyCodeInput.readOnly = true;
                        elements.registerBtn.disabled = true;
                    });
                } else {
                    elements.sendVerifyBtn.disabled = false;
                    elements.sendVerifyBtn.textContent = '發送驗證碼';
                    elements.email.readOnly = false;
                }
            } catch (error) {
                console.error('Send verify code error:', error);
                elements.sendVerifyBtn.disabled = false;
                elements.sendVerifyBtn.textContent = '發送驗證碼';
                elements.email.readOnly = false;
            }
        };
 
        // 綁定驗證碼輸入事件
        elements.verifyCodeInput.oninput = async function() {
            if (this.value.length === 6) {
                this.readOnly = true;
                
                if (await verificationSystem.verifyCode(elements.email.value, this.value)) {
                    elements.registerBtn.disabled = false;
                    clearInterval(verificationSystem.timerId);
                    elements.timer.textContent = '驗證成功';
                } else {
                    this.value = '';
                    this.readOnly = false;
                }
            }
        };
 
        console.log('RegSystem init complete');
    }
 }
 
 // 專案管理系統
 class ProjectSystem {
    static initSorting() {
        const sortSelect = document.getElementById('sortProjects');
        if (sortSelect) {
            sortSelect.addEventListener('change', function() {
                const currentUrl = new URL(window.location.href);
                currentUrl.searchParams.set('sort', this.value);
                window.location.href = currentUrl.toString();
            });
 
            const urlParams = new URLSearchParams(window.location.search);
            const currentSort = urlParams.get('sort') || 'created_desc';
            sortSelect.value = currentSort;
        }
    }
 
    static initDeleteButtons() {
        document.querySelectorAll('.delete-button').forEach(button => {
            button.addEventListener('click', function() {
                if (confirm('確定要刪除這個專案嗎？')) {
                    showAlert('專案刪除中...', 'info');
                    const projectId = this.dataset.projectId;
                    window.location.href = `/delete_project/${projectId}`;
                }
            });
        });
    }
 
    static initFormValidation() {
        const form = document.querySelector('#createProjectForm');
        if (!form) return;
        
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            
            if (!ProjectSystem.validateRequiredFields(form)) return;
            if (!ProjectSystem.validateDates()) return;
            
            form.submit();
        });
 
        form.querySelectorAll('input, select, textarea').forEach(element => {
            element.addEventListener('input', function() {
                if (this.value.trim()) {
                    this.classList.remove('is-invalid');
                }
            });
        });
    }
 
    static validateRequiredFields(form) {
        let isValid = true;
        form.querySelectorAll('[required]').forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                ProjectSystem.showFieldError(field);
            } else {
                field.classList.remove('is-invalid');
            }
        });
        return isValid;
    }
 
    static validateDates() {
        const startDate = new Date(document.getElementById('projectStartDate').value);
        const endDate = new Date(document.getElementById('projectEndDate').value);
        const analysisStartDate = new Date(document.getElementById('analysisStartDate').value);
        const analysisEndDate = new Date(document.getElementById('analysisEndDate').value);
 
        if (endDate < startDate) {
            showAlert('專案結束日期必須晚於開始日期', 'danger');
            return false;
        }
 
        if (analysisEndDate < analysisStartDate) {
            showAlert('分析結束日期必須晚於開始日期', 'danger');
            return false;
        }
 
        return true;
    }
 
    static showFieldError(field) {
        field.classList.add('is-invalid');
        if (!field.nextElementSibling?.classList.contains('invalid-feedback')) {
            const feedback = document.createElement('div');
            feedback.classList.add('invalid-feedback');
            feedback.textContent = '此欄位為必填';
            field.parentNode.appendChild(feedback);
        }
    }
 
    static initEditButtons() {
        document.querySelectorAll('.edit-button').forEach(button => {
            button.addEventListener('click', function() {
                const projectId = this.dataset.projectId;
                const nextStepBtn = document.getElementById('nextStepBtn');
                if (nextStepBtn) {
                    nextStepBtn.href = `/stakeholder_form/${projectId}`;
                    nextStepBtn.style.display = 'inline-block';
                }
                
                fetch(`/get_project/${projectId}`)
                    .then(response => response.json())
                    .then(project => {
                        ProjectSystem.fillEditForm(project, projectId);
                    })
                    .catch(error => {
                        showAlert('獲取專案資料失敗', 'danger');
                    });
            });
        });
    }
 
    static fillEditForm(project, projectId) {
        const form = document.getElementById('editProjectForm');
        if (!form) return;
 
        form.action = `/update_project/${projectId}`;
        
        Object.keys(project).forEach(key => {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) input.value = project[key];
        });
    }
 
    static initDeleteConfirmation() {
        const deleteModal = document.getElementById('deleteConfirmModal');
        if (!deleteModal) return;  // 如果模態框不存在，直接返回

        const modal = new bootstrap.Modal(deleteModal, {
            keyboard: false
        });

        let projectToDelete = null;
 
        document.querySelectorAll('.delete-button').forEach(button => {
            button.addEventListener('click', function() {
                projectToDelete = this.dataset.projectId;
                deleteModal.show();
            });
        });
 
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', function() {
                if (projectToDelete) {
                    showAlert('正在刪除專案...', 'info');
                    const deleteUrl = `/delete_project/${projectToDelete}`;
                    window.location.href = deleteUrl;
                    deleteModal.hide();
                }
            });
        }
    }
    
    static checkModalParam() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('openModal') === 'create') {
            const createProjectModal = new bootstrap.Modal(document.getElementById('createProjectModal'));
            createProjectModal.show();
        }
    }
 
    static initViewSwitch() {
        const viewButtons = document.querySelectorAll('.view-switch .btn');
        const projectsContainer = document.getElementById('projectsContainer');
        
        if (!viewButtons.length || !projectsContainer) return;
        
        viewButtons.forEach(button => {
            button.addEventListener('click', function() {
                // 更新按鈕狀態
                viewButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                
                // 切換視圖
                const viewType = this.dataset.view;
                projectsContainer.className = viewType + '-view';
                
                // 顯示/隱藏對應的項目
                document.querySelectorAll('.list-view-item').forEach(item => {
                    item.style.display = viewType === 'list' ? 'block' : 'none';
                });
                document.querySelectorAll('.grid-view-item').forEach(item => {
                    item.style.display = viewType === 'grid' ? 'block' : 'none';
                });
            });
        });
    }
 
    static initSearch() {
        const searchInput = document.getElementById('searchProject');
        if (!searchInput) return;

        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const currentView = document.getElementById('projectsContainer').className;
            const isListView = currentView.includes('list-view');
            
            // 選擇當前視圖的項目
            const selector = isListView ? '.list-view-item' : '.grid-view-item';
            document.querySelectorAll(selector).forEach(item => {
                const projectName = item.querySelector('h5').textContent.toLowerCase();
                const orgName = item.querySelector('.bi-building').parentElement.textContent.toLowerCase();
                const shouldShow = projectName.includes(searchTerm) || orgName.includes(searchTerm);
                item.style.display = shouldShow ? 'block' : 'none';
            });
        });
    }
 
    static initFilters() {
        const filterButtons = document.querySelectorAll('[data-filter]');
        if (!filterButtons.length) return;
        
        filterButtons.forEach(button => {
            button.addEventListener('click', function() {
                // 更新按鈕狀態
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');

                const filter = this.dataset.filter;
                const currentView = document.getElementById('projectsContainer').className;
                const isListView = currentView.includes('list-view');
                
                // 選擇當前視圖的項目
                const items = document.querySelectorAll(isListView ? '.list-view-item' : '.grid-view-item');
                items.forEach(item => {
                    const badge = item.querySelector('.project-badge');
                    if (!badge) return;
                    
                    const hasScore = badge.textContent.trim() !== '未評分';
                    const shouldShow = 
                        filter === 'all' || 
                        (filter === 'completed' && hasScore) || 
                        (filter === 'in-progress' && !hasScore);
                        
                    item.style.display = shouldShow ? 'block' : 'none';
                });
            });
        });
    }
 }
 
// 使用 Fetch API 或 Axios 進行 API 調用
async function getProjects() {
    try {
        const response = await fetch('/api/projects');
        const data = await response.json();
        if (data.status === 'success') {
            updateProjectsList(data.data);
        }
    } catch (error) {
        showAlert('獲取專案列表失敗', 'danger');
    }
}

async function createProject(projectData) {
    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(projectData)
        });
        const data = await response.json();
        if (data.status === 'success') {
            showAlert('專案創建成功', 'success');
            getProjects();  // 重新載入專案列表
        }
    } catch (error) {
        showAlert('創建專案失敗', 'danger');
    }
}
 
// 頁面載入時也執行初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('頁面載入完成，開始初始化');
    
    // 初始化各個系統
    ProjectSystem.initSorting();
    ProjectSystem.initDeleteButtons();
    ProjectSystem.initFormValidation();
    ProjectSystem.initEditButtons();
    ProjectSystem.initDeleteConfirmation();
    ProjectSystem.checkModalParam();
    ProjectSystem.initViewSwitch();
    ProjectSystem.initSearch();
    ProjectSystem.initFilters();
    
    // 初始化註冊系統
    RegisterSystem.init();
    
    // 處理 Flash 訊息
    const flashDiv = document.getElementById('flashMessages');
    if (flashDiv) {
        const messages = flashDiv.getElementsByTagName('div');
        Array.from(messages).forEach(messageDiv => {
            const message = messageDiv.getAttribute('data-message');
            const category = messageDiv.getAttribute('data-category');
            if (message && category) {
                showAlert(message, category);
            }
            messageDiv.remove();
        });
    }
});
 
// 導出全域函數和類
window.showAlert = showAlert;
window.ProjectSystem = ProjectSystem;
window.VerificationSystem = VerificationSystem;
window.RegisterSystem = RegisterSystem;