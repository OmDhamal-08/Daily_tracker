// API Base URL - will be relative on Vercel
const API_BASE_URL = window.location.origin;

let currentTab = 'weekly';

document.addEventListener('DOMContentLoaded', function() {
    const today = new Date();
    const todayFormatted = formatDate(today);
    document.getElementById('date').value = todayFormatted;
    document.getElementById('date').max = todayFormatted;
    
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    document.getElementById('startDate').value = formatDate(weekAgo);
    document.getElementById('endDate').value = todayFormatted;
    
    updateDateInfo();
    loadStats();
    loadTodayStatus();
    loadWeeklyReports();
    loadMonthlyReports();
    loadHistory();
    
    setupEventListeners();
});

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function updateDateInfo() {
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    
    const startDate = new Date(now.getFullYear(), 0, 1);
    const days = Math.floor((now - startDate) / (24 * 60 * 60 * 1000));
    const weekNumber = Math.ceil((days + startDate.getDay() + 1) / 7);
    const monthName = now.toLocaleDateString('en-US', { month: 'long' });
    
    document.getElementById('current-date').textContent = dateStr;
    document.getElementById('week-number').textContent = weekNumber;
    document.getElementById('month-name').textContent = monthName;
}

function setupEventListeners() {
    document.getElementById('dailyForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            date: document.getElementById('date').value,
            gym: document.getElementById('gym').checked,
            dsa: document.getElementById('dsa').checked,
            ml: document.getElementById('ml').checked,
            django: document.getElementById('django').checked,
            sql: document.getElementById('sql').checked,
            project_work: document.getElementById('project_work').checked,
            aws: document.getElementById('aws').checked   // <-- NEW
        };
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/daily/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                showToast('Checklist saved successfully!', 'success');
                clearForm();
                loadTodayStatus();
                loadStats();
                loadWeeklyReports();
                loadMonthlyReports();
                loadHistory();
            } else {
                const error = await response.json();
                showToast(`Error: ${error.detail}`, 'error');
            }
        } catch (error) {
            showToast('Network error. Please check if server is running.', 'error');
        }
    });
    
    document.getElementById('loadHistory').addEventListener('click', loadHistory);
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tab = this.getAttribute('data-tab');
            switchTab(tab);
        });
    });
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats/`);
        if (response.ok) {
            const stats = await response.json();
            const statsHtml = `
                <div class="stat-item">
                    <span class="stat-value">${stats.total_days_tracked}</span>
                    <span class="stat-label">Days Tracked</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${stats.total_weeks_reported || 0}</span>
                    <span class="stat-label">Weeks</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${stats.total_months_reported || 0}</span>
                    <span class="stat-label">Months</span>
                </div>
            `;
            document.getElementById('stats').innerHTML = statsHtml;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('stats').innerHTML = '<p>Loading...</p>';
    }
}

async function loadTodayStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/today`);
        if (response.ok) {
            const data = await response.json();
            
            const statusHtml = `
                <div class="status-item ${data.gym ? 'completed' : 'pending'}">
                    <h4>GYM</h4>
                    <p>${data.gym ? '✓ Completed' : '✗ Not checked'}</p>
                </div>
                <div class="status-item ${data.dsa ? 'completed' : 'pending'}">
                    <h4>DSA</h4>
                    <p>${data.dsa ? '✓ Completed' : '✗ Not checked'}</p>
                </div>
                <div class="status-item ${data.ml ? 'completed' : 'pending'}">
                    <h4>ML</h4>
                    <p>${data.ml ? '✓ Completed' : '✗ Not checked'}</p>
                </div>
                <div class="status-item ${data.django ? 'completed' : 'pending'}">
                    <h4>Django</h4>
                    <p>${data.django ? '✓ Completed' : '✗ Not checked'}</p>
                </div>
                <div class="status-item ${data.sql ? 'completed' : 'pending'}">
                    <h4>SQL</h4>
                    <p>${data.sql ? '✓ Completed' : '✗ Not checked'}</p>
                </div>
                <div class="status-item ${data.project_work ? 'completed' : 'pending'}">
                    <h4>Project</h4>
                    <p>${data.project_work ? '✓ Completed' : '✗ Not checked'}</p>
                </div>
                <div class="status-item ${data.aws ? 'completed' : 'pending'}">
                    <h4>AWS</h4>
                    <p>${data.aws ? '✓ Completed' : '✗ Not checked'}</p>
                </div>
            `;
            
            document.getElementById('todayStatus').innerHTML = statusHtml;
            
            if (data.exists) {
                document.getElementById('gym').checked = data.gym;
                document.getElementById('dsa').checked = data.dsa;
                document.getElementById('ml').checked = data.ml;
                document.getElementById('django').checked = data.django;
                document.getElementById('sql').checked = data.sql;
                document.getElementById('project_work').checked = data.project_work;
                document.getElementById('aws').checked = data.aws;
            } else {
                clearForm();
            }
        }
    } catch (error) {
        console.error('Error loading today status:', error);
        // Fallback HTML (omitted for brevity, but keep existing)
    }
}

async function loadHistory() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    try {
        let url = `${API_BASE_URL}/api/daily/`;
        if (startDate && endDate) url += `?start_date=${startDate}&end_date=${endDate}`;
        
        const response = await fetch(url);
        if (response.ok) {
            const history = await response.json();
            if (history.length === 0) {
                document.getElementById('historyList').innerHTML = '<p>No history found.</p>';
                return;
            }
            
            let historyHtml = '';
            history.forEach(item => {
                const date = new Date(item.date).toLocaleDateString('en-US', {
                    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric'
                });
                
                const completedTasks = [];
                if (item.gym) completedTasks.push('GYM');
                if (item.dsa) completedTasks.push('DSA');
                if (item.ml) completedTasks.push('ML');
                if (item.django) completedTasks.push('Django');
                if (item.sql) completedTasks.push('SQL');
                if (item.project_work) completedTasks.push('Project');
                if (item.aws) completedTasks.push('AWS');
                
                const tasksHtml = completedTasks.length > 0 
                    ? completedTasks.map(task => `<span class="task-badge completed">${task}</span>`).join('')
                    : '<span class="task-badge">No tasks completed</span>';
                
                historyHtml += `
                    <div class="history-item">
                        <div class="history-date">${date}</div>
                        <div class="history-tasks">${tasksHtml}</div>
                    </div>
                `;
            });
            document.getElementById('historyList').innerHTML = historyHtml;
        }
    } catch (error) {
        console.error('Error loading history:', error);
        document.getElementById('historyList').innerHTML = '<p>Error loading history</p>';
    }
}

async function loadWeeklyReports() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/weekly/`);
        if (response.ok) {
            const reports = await response.json();
            if (reports.length === 0) {
                document.getElementById('weeklyReports').innerHTML = '<p>No weekly reports yet.</p>';
                return;
            }
            
            let reportsHtml = '';
            reports.forEach(report => {
                const startDate = new Date(report.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                const endDate = new Date(report.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                
                reportsHtml += `
                    <div class="report-item">
                        <div class="report-header">
                            <h4>Week ${report.week_number}, ${report.year} (${startDate} - ${endDate})</h4>
                            <div class="report-score">${report.total_score.toFixed(1)}%</div>
                        </div>
                        <div class="progress-bars">
                            <div><small>GYM: ${report.gym_percentage.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.gym_percentage,100)}%"></div></div></div>
                            <div><small>DSA: ${report.dsa_percentage.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.dsa_percentage,100)}%"></div></div></div>
                            <div><small>ML: ${report.ml_percentage.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.ml_percentage,100)}%"></div></div></div>
                            <div><small>Django: ${report.django_percentage.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.django_percentage,100)}%"></div></div></div>
                            <div><small>SQL: ${report.sql_percentage.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.sql_percentage,100)}%"></div></div></div>
                            <div><small>Project: ${report.project_percentage.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.project_percentage,100)}%"></div></div></div>
                            <div><small>AWS: ${report.aws_percentage.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.aws_percentage,100)}%"></div></div></div>
                        </div>
                    </div>
                `;
            });
            document.getElementById('weeklyReports').innerHTML = reportsHtml;
        }
    } catch (error) {
        console.error('Error loading weekly reports:', error);
        document.getElementById('weeklyReports').innerHTML = '<p>Loading...</p>';
    }
}

async function loadMonthlyReports() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/monthly/`);
        if (response.ok) {
            const reports = await response.json();
            if (reports.length === 0) {
                document.getElementById('monthlyReports').innerHTML = '<p>No monthly reports yet.</p>';
                return;
            }
            
            let reportsHtml = '';
            reports.forEach(report => {
                const monthName = new Date(report.year, report.month - 1).toLocaleDateString('en-US', { month: 'long' });
                reportsHtml += `
                    <div class="report-item">
                        <div class="report-header">
                            <h4>${monthName} ${report.year}</h4>
                            <div class="report-score">${report.total_days_tracked} days</div>
                        </div>
                        <div class="progress-bars">
                            <div><small>GYM: ${report.avg_gym.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.avg_gym,100)}%"></div></div></div>
                            <div><small>DSA: ${report.avg_dsa.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.avg_dsa,100)}%"></div></div></div>
                            <div><small>ML: ${report.avg_ml.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.avg_ml,100)}%"></div></div></div>
                            <div><small>Django: ${report.avg_django.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.avg_django,100)}%"></div></div></div>
                            <div><small>SQL: ${report.avg_sql.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.avg_sql,100)}%"></div></div></div>
                            <div><small>Project: ${report.avg_project.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.avg_project,100)}%"></div></div></div>
                            <div><small>AWS: ${report.avg_aws.toFixed(1)}%</small><div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(report.avg_aws,100)}%"></div></div></div>
                        </div>
                    </div>
                `;
            });
            document.getElementById('monthlyReports').innerHTML = reportsHtml;
        }
    } catch (error) {
        console.error('Error loading monthly reports:', error);
        document.getElementById('monthlyReports').innerHTML = '<p>Loading...</p>';
    }
}

function switchTab(tab) {
    if (currentTab === tab) return;
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-tab') === tab) btn.classList.add('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
        if (content.id === `${tab}Tab`) content.classList.add('active');
    });
    currentTab = tab;
}

function clearForm() {
    document.getElementById('gym').checked = false;
    document.getElementById('dsa').checked = false;
    document.getElementById('ml').checked = false;
    document.getElementById('django').checked = false;
    document.getElementById('sql').checked = false;
    document.getElementById('project_work').checked = false;
    document.getElementById('aws').checked = false;
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const icon = toast.querySelector('.toast-icon');
    const msgSpan = toast.querySelector('.toast-message');
    
    msgSpan.textContent = message;
    
    if (type === 'success') {
        icon.className = 'toast-icon fas fa-check-circle';
        toast.style.background = '#48bb78';
    } else if (type === 'error') {
        icon.className = 'toast-icon fas fa-exclamation-circle';
        toast.style.background = '#f56565';
    } else {
        icon.className = 'toast-icon fas fa-info-circle';
        toast.style.background = '#2d3748';
    }
    
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// Auto-refresh
setInterval(() => {
    loadTodayStatus();
    loadStats();
}, 30000);