/**
 * 三方法对比看板 - 主逻辑
 */

// 全局状态
let allCases = [];
let filteredCases = [];
let currentIndex = 0;

// DOM元素
const elements = {
    caseSelect: document.getElementById('caseSelect'),
    prevBtn: document.getElementById('prevBtn'),
    nextBtn: document.getElementById('nextBtn'),
    caseCounter: document.getElementById('caseCounter'),
    errorFilter: document.getElementById('errorFilter'),
    typeFilter: document.getElementById('typeFilter'),
    caseId: document.getElementById('caseId'),
    groundTruth: document.getElementById('groundTruth'),
    platform: document.getElementById('platform'),
    complexity: document.getElementById('complexity'),
    description: document.getElementById('description'),
    baselineStatus: document.getElementById('baselineStatus'),
    baselineResponse: document.getElementById('baselineResponse'),
    baselineParsed: document.getElementById('baselineParsed'),
    ragStatus: document.getElementById('ragStatus'),
    ragResponse: document.getElementById('ragResponse'),
    ragParsed: document.getElementById('ragParsed'),
    agentStatus: document.getElementById('agentStatus'),
    agentChain: document.getElementById('agentChain'),
    agentParsed: document.getElementById('agentParsed'),
    agentRemediation: document.getElementById('agentRemediation')
};

// 加载数据
async function loadData() {
    try {
        const response = await fetch('data/merged.json');
        const data = await response.json();

        allCases = data.cases;
        filteredCases = [...allCases];

        // 初始化筛选器
        initFilters(data.index.filters);

        // 初始化案例选择
        updateCaseSelect();

        // 显示第一个案例
        if (filteredCases.length > 0) {
            renderCase(0);
        }
    } catch (error) {
        console.error('加载数据失败:', error);
        alert('加载数据失败，请确保已运行预处理脚本生成 data/merged.json');
    }
}

// 初始化筛选器
function initFilters(filters) {
    // 错误类型筛选
    elements.errorFilter.innerHTML = '';
    filters.error_types.forEach(item => {
        const option = document.createElement('option');
        option.value = item.value;
        option.textContent = item.label;
        elements.errorFilter.appendChild(option);
    });

    // 违规类型筛选
    elements.typeFilter.innerHTML = '';
    filters.violation_types.forEach(item => {
        const option = document.createElement('option');
        option.value = item.value;
        option.textContent = item.label;
        elements.typeFilter.appendChild(option);
    });
}

// 更新案例选择下拉框
function updateCaseSelect() {
    elements.caseSelect.innerHTML = '';
    filteredCases.forEach((c, idx) => {
        const option = document.createElement('option');
        option.value = idx;
        option.textContent = c.case_id;
        elements.caseSelect.appendChild(option);
    });
}

// 应用筛选
function applyFilters() {
    const errorFilter = elements.errorFilter.value;
    const typeFilter = elements.typeFilter.value;

    filteredCases = allCases.filter(c => {
        // 错误类型筛选
        if (errorFilter !== 'all') {
            if (errorFilter === 'baseline_error' && c.baseline.is_correct) return false;
            if (errorFilter === 'rag_error' && c.rag.is_correct) return false;
            if (errorFilter === 'agent_error' && c.agent.is_correct) return false;
            if (errorFilter === 'inconsistent') {
                const results = [c.baseline.is_correct, c.rag.is_correct, c.agent.is_correct];
                const allSame = results.every(r => r === results[0]);
                if (allSame) return false;
            }
        }

        // 违规类型筛选
        if (typeFilter !== 'all') {
            if (c.ground_truth.violation_type !== typeFilter) return false;
        }

        return true;
    });

    updateCaseSelect();
    currentIndex = 0;

    if (filteredCases.length > 0) {
        renderCase(0);
    } else {
        clearDisplay();
        elements.caseCounter.textContent = '0 / 0';
    }
}

// 清空显示
function clearDisplay() {
    elements.caseId.textContent = '-';
    elements.groundTruth.textContent = '-';
    elements.platform.textContent = '-';
    elements.complexity.textContent = '-';
    elements.description.textContent = '无匹配案例';
    elements.baselineStatus.textContent = '-';
    elements.baselineStatus.className = 'status-badge';
    elements.baselineResponse.textContent = '-';
    elements.baselineParsed.innerHTML = '-';
    elements.ragStatus.textContent = '-';
    elements.ragStatus.className = 'status-badge';
    elements.ragResponse.textContent = '-';
    elements.ragParsed.innerHTML = '-';
    elements.agentStatus.textContent = '-';
    elements.agentStatus.className = 'status-badge';
    elements.agentChain.innerHTML = '-';
    elements.agentParsed.innerHTML = '-';
    elements.agentRemediation.innerHTML = '-';
}

// 渲染案例
function renderCase(index) {
    if (index < 0 || index >= filteredCases.length) return;

    currentIndex = index;
    const c = filteredCases[index];

    // 更新导航状态
    elements.caseSelect.value = index;
    elements.caseCounter.textContent = `${index + 1} / ${filteredCases.length}`;
    elements.prevBtn.disabled = index === 0;
    elements.nextBtn.disabled = index === filteredCases.length - 1;

    // 案例信息
    elements.caseId.textContent = c.case_id;
    const gt = c.ground_truth;
    elements.groundTruth.textContent = gt.is_violation
        ? `违规 - ${gt.violation_type}`
        : '合规';
    elements.platform.textContent = gt.platform || '-';
    elements.complexity.textContent = gt.complexity || '-';
    elements.description.textContent = c.case_description || '-';

    // Baseline
    renderMethodResult('baseline', c.baseline);

    // RAG
    renderMethodResult('rag', c.rag);

    // Agent
    renderAgentResult(c.agent);
}

// 渲染方法结果（Baseline/RAG）
function renderMethodResult(method, data) {
    const statusEl = elements[method + 'Status'];
    const responseEl = elements[method + 'Response'];
    const parsedEl = elements[method + 'Parsed'];

    if (!data.success) {
        statusEl.textContent = '失败';
        statusEl.className = 'status-badge failed';
        responseEl.textContent = '执行失败';
        parsedEl.innerHTML = '-';
        return;
    }

    // 状态
    statusEl.textContent = data.is_correct ? '正确' : '错误';
    statusEl.className = 'status-badge ' + (data.is_correct ? 'correct' : 'incorrect');

    // 原始回答
    responseEl.textContent = data.llm_response || '-';

    // 解析结果
    const pred = data.prediction || {};
    parsedEl.innerHTML = renderParsedResult(pred, data.type_correct, data.match_details);
}

// 渲染Agent结果
function renderAgentResult(data) {
    const statusEl = elements.agentStatus;
    const chainEl = elements.agentChain;
    const parsedEl = elements.agentParsed;
    const remediationEl = elements.agentRemediation;

    if (!data.success) {
        statusEl.textContent = '失败';
        statusEl.className = 'status-badge failed';
        chainEl.innerHTML = '执行失败';
        parsedEl.innerHTML = '-';
        remediationEl.innerHTML = '-';
        return;
    }

    // 状态
    statusEl.textContent = data.is_correct ? '正确' : '错误';
    statusEl.className = 'status-badge ' + (data.is_correct ? 'correct' : 'incorrect');

    // 推理链
    const chain = data.reasoning_chain || [];
    if (chain.length > 0) {
        chainEl.innerHTML = chain.map((step, idx) => {
            // 尝试解析步骤标题和内容
            const match = step.match(/^(步骤\d+[：:]\s*[^-–]+)[-–]\s*(.*)$/);
            if (match) {
                return `<div class="step">
                    <div class="step-title">${match[1]}</div>
                    <div class="step-content">${match[2]}</div>
                </div>`;
            }
            return `<div class="step">${step}</div>`;
        }).join('');
    } else {
        chainEl.innerHTML = '<div class="step">无推理链</div>';
    }

    // 解析结果
    const pred = data.prediction || {};
    parsedEl.innerHTML = renderParsedResult(pred, data.type_correct, data.match_details);

    // 整改建议
    const remediation = data.remediation || {};
    if (remediation.remediation_steps && remediation.remediation_steps.length > 0) {
        remediationEl.innerHTML = remediation.remediation_steps.map(step =>
            `<div class="remediation-step">
                <div class="step-action">${step.step}. ${step.action}</div>
                <div class="step-meta">法律依据: ${step.legal_basis || '-'} | 优先级: ${step.priority || '-'}</div>
            </div>`
        ).join('');
    } else {
        remediationEl.innerHTML = '无整改建议';
    }
}

// 渲染解析结果
function renderParsedResult(pred, typeCorrect, matchDetails) {
    const isViolation = pred.is_violation;
    const violationClass = isViolation ? 'violation' : 'compliance';

    let html = `
        <div class="field">
            <div class="field-label">是否违规:</div>
            <div class="field-value ${violationClass}">${isViolation ? '是' : '否'}</div>
        </div>
        <div class="field">
            <div class="field-label">违规类型:</div>
            <div class="field-value">${pred.violation_type || '-'} ${typeCorrect ? '✓' : '✗'}</div>
        </div>
        <div class="field">
            <div class="field-label">置信度:</div>
            <div class="field-value">${pred.confidence ? (pred.confidence * 100).toFixed(0) + '%' : '-'}</div>
        </div>
        <div class="field">
            <div class="field-label">法律依据:</div>
            <div class="field-value">${pred.legal_basis || '-'}</div>
        </div>
        <div class="field">
            <div class="field-label">推理:</div>
            <div class="field-value">${pred.reasoning || '-'}</div>
        </div>
    `;

    if (matchDetails && matchDetails.details) {
        html += `
            <div class="field">
                <div class="field-label">匹配详情:</div>
                <div class="field-value">${matchDetails.details}</div>
            </div>
        `;
    }

    return html;
}

// 导航函数
function goToCase(index) {
    if (index >= 0 && index < filteredCases.length) {
        renderCase(index);
    }
}

function prevCase() {
    goToCase(currentIndex - 1);
}

function nextCase() {
    goToCase(currentIndex + 1);
}

// 事件绑定
function bindEvents() {
    // 导航
    elements.caseSelect.addEventListener('change', (e) => {
        goToCase(parseInt(e.target.value));
    });

    elements.prevBtn.addEventListener('click', prevCase);
    elements.nextBtn.addEventListener('click', nextCase);

    // 筛选
    elements.errorFilter.addEventListener('change', applyFilters);
    elements.typeFilter.addEventListener('change', applyFilters);

    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'SELECT') return;

        if (e.key === 'ArrowLeft') {
            prevCase();
        } else if (e.key === 'ArrowRight') {
            nextCase();
        }
    });
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    loadData();
});
