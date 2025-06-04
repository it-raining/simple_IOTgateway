document.addEventListener('DOMContentLoaded', function () {
    const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim();
    const textColorMuted = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim();

    // --- Dữ liệu JSON cho cấu trúc thư mục ---

    let currentPath = [];



    // --- Lấy các phần tử DOM ---
    const folderView = document.getElementById('folder-view');
    const chartView = document.getElementById('chart-view');
    const tabButtons = document.querySelectorAll('.tab-button');
    const breadcrumbsContainer = document.querySelector('.breadcrumbs');
    const fileTableBody = document.querySelector('.file-table tbody');
    const searchInput = document.getElementById('file-search-input');
    const sidebarLinks = document.querySelectorAll('.sidebar-nav a[data-view]');
    const fileSystemData = [
        {
            name: 'Báo cáo', type: 'folder', lastModified: '2024-05-20', children: [
                { name: 'Báo cáo Q1-2024.pdf', type: 'file', size: '2.5 MB', lastModified: '2024-04-15' },
                { name: 'Báo cáo Q2-2024.pdf', type: 'file', size: '3.1 MB', lastModified: '2024-07-10' },
                {
                    name: 'Năm 2023', type: 'folder', lastModified: '2024-01-05', children: [
                        { name: 'Tong_ket_2023.docx', type: 'file', size: '800 KB', lastModified: '2023-12-28' }
                    ]
                }
            ]
        },
        {
            name: 'Tài liệu kỹ thuật', type: 'folder', lastModified: '2024-06-11', children: [
                { name: 'API_Documentation.md', type: 'file', size: '1.2 MB', lastModified: '2024-06-10' },
                { name: 'Database_Schema.png', type: 'file', size: '450 KB', lastModified: '2024-05-30' }
            ]
        },
        { name: 'Hình ảnh', type: 'folder', lastModified: '2024-07-15', children: [] },
        { name: 'README.md', type: 'file', size: '1 KB', lastModified: '2024-01-01' }
    ];

    //gọi API
    // let fileSystemData = [];

    // async function main() {
    //     // Bước 1: Gọi API để lấy dữ liệu
    //     try {
    //         // Hiển thị thông báo đang tải... (Tùy chọn)
    //         fileTableBody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding: 20px;">Đang tải dữ liệu...</td></tr>`;

    //         // Thay thế URL này bằng URL API thực tế của bạn
    //         const response = await fetch('https://api.npoint.io/5f5e2278a5bac03d274e'); // Ví dụ dùng API mock

    //         if (!response.ok) {
    //             // Nếu API trả về lỗi (ví dụ: 404, 500), ném ra một lỗi
    //             throw new Error(`Lỗi HTTP: ${response.status}`);
    //         }

    //         // Gán dữ liệu lấy được vào biến toàn cục
    //         fileSystemData = await response.json();

    //         // Bước 2: Sau khi có dữ liệu, render giao diện lần đầu
    //         renderFileSystem();

    //     } catch (error) {
    //         console.error('Không thể khởi tạo ứng dụng:', error);
    //         // Hiển thị thông báo lỗi trên UI
    //         fileTableBody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding: 20px; color: red;">Không thể tải dữ liệu từ máy chủ. Vui lòng thử lại sau.</td></tr>`;
    //     }

    //     // Bước 3: Đăng ký các trình nghe sự kiện sau khi đã sẵn sàng
    //     setupEventListeners();
    // }

    // function setupEventListeners() {
    //     tabButtons.forEach(button => {
    //         button.addEventListener('click', () => switchToTab(button.dataset.tab));
    //     });

    //     sidebarLinks.forEach(link => {
    //         link.addEventListener('click', (e) => {
    //             e.preventDefault();
    //             switchToTab(link.dataset.view);
    //         });
    //     });

    //     folderView.addEventListener('click', (e) => {
    //         if (searchInput.value.trim()) return;
    //         handleNavigation(e);
    //     });

    //     searchInput.addEventListener('keyup', renderFileSystem);
    // }

    function switchToTab(viewId) {
        if (!viewId || viewId === 'query-view') {
            // Tạm thời không làm gì nếu click vào Query Data hoặc không có viewId
            console.log("Tab này chưa có chức năng.");
            return;
        }

        // 1. Cập nhật trạng thái 'active' cho các nút tab ở header
        tabButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === viewId);
        });

        // 2. Cập nhật trạng thái 'active' cho các mục trong sidebar
        sidebarLinks.forEach(link => {
            link.parentElement.classList.toggle('active', link.dataset.view === viewId);
        });

        // 3. Hiển thị/ẩn các tab content tương ứng
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === viewId);
        });

        // 4. Khởi tạo biểu đồ nếu chuyển sang tab biểu đồ
        if (viewId === 'chart-view') {
            initializeCharts();
        }
    }


    // --- Logic chuyển Tab (sử dụng hàm mới) ---
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            switchToTab(button.dataset.tab);
        });
    });

    // ===== THÊM LOGIC MỚI: Lắng nghe sự kiện click trên sidebar =====
    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault(); // Ngăn hành vi mặc định của thẻ <a>
            switchToTab(link.dataset.view);
        });
    });

    function searchAllFiles(nodes, searchTerm, path = []) {
        let results = [];
        const lowerCaseSearchTerm = searchTerm.toLowerCase();

        for (const node of nodes) {
            const currentItemPath = [...path, node.name];
            if (node.name.toLowerCase().includes(lowerCaseSearchTerm)) {
                results.push({ ...node, fullPath: currentItemPath.join(' / ') });
            }

            if (node.type === 'folder' && node.children) {
                results = results.concat(searchAllFiles(node.children, searchTerm, currentItemPath));
            }
        }
        return results;
    }

    function renderFileSystem() {
        const searchTerm = searchInput.value.trim();
        fileTableBody.innerHTML = '';

        if (searchTerm) {
            breadcrumbsContainer.innerHTML = `Kết quả tìm kiếm cho: <strong>"${searchTerm}"</strong>`;
            breadcrumbsContainer.style.textAlign = 'center';

            const searchResults = searchAllFiles(fileSystemData, searchTerm);

            if (searchResults.length === 0) {
                fileTableBody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding: 20px;">Không tìm thấy file hoặc thư mục nào.</td></tr>`;
                return;
            }

            searchResults.forEach(item => {
                const icon = item.type === 'folder' ? '📁' : '📄';
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        <div class="file-name ${item.type}-item">
                            <span class="file-icon">${icon}</span>
                            <div>
                                ${item.name}
                                <span class="file-path">${item.fullPath}</span>
                            </div>
                        </div>
                    </td>
                    <td>${item.lastModified}</td>
                    <td class="file-size">${item.size || '--'}</td>
                `;
                fileTableBody.appendChild(row);
            });
        }
        else {
            breadcrumbsContainer.style.textAlign = 'left';

            let currentItems = fileSystemData;
            try {
                for (const pathPart of currentPath) {
                    const folder = currentItems.find(item => item.name === pathPart && item.type === 'folder');
                    currentItems = folder.children;
                }
            } catch (e) {
                console.error("Path không hợp lệ:", currentPath);
                currentPath = [];
            }

            breadcrumbsContainer.innerHTML = `<a data-path-index="-1">Thư mục gốc</a>`;
            currentPath.forEach((part, index) => {
                breadcrumbsContainer.innerHTML += `<span>/</span><a data-path-index="${index}">${part}</a>`;
            });

            currentItems.sort((a, b) => {
                if (a.type === 'folder' && b.type !== 'folder') return -1;
                if (a.type !== 'folder' && b.type === 'folder') return 1;
                return a.name.localeCompare(b.name);
            }).forEach(item => {
                const icon = item.type === 'folder' ? '📁' : '📄';
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        <div class="file-name ${item.type}-item" data-name="${item.name}" data-type="${item.type}">
                            <span class="file-icon">${icon}</span>
                            ${item.name}
                        </div>
                    </td>
                    <td>${item.lastModified}</td>
                    <td class="file-size">${item.size || '--'}</td>
                `;
                fileTableBody.appendChild(row);
            });
        }
    }

    folderView.addEventListener('click', (e) => {
        if (searchInput.value.trim()) {
            console.log("Xóa nội dung tìm kiếm để bắt đầu duyệt thư mục.");
            return;
        }

        const folderLink = e.target.closest('.folder-item');
        const breadcrumbLink = e.target.closest('.breadcrumbs a');

        if (folderLink) {
            const folderName = folderLink.dataset.name;
            currentPath.push(folderName);
            renderFileSystem();
        } else if (breadcrumbLink) {
            const pathIndex = parseInt(breadcrumbLink.dataset.pathIndex, 10);
            currentPath = currentPath.slice(0, pathIndex + 1);
            renderFileSystem();
        }
    });

    searchInput.addEventListener('keyup', () => {
        renderFileSystem();
    });

    let lineChartInstance = null;
    let donutChartInstance = null;

    function initializeCharts() {
        const lineChartCanvasElement = document.getElementById('lineChartCanvas');
        if (lineChartCanvasElement && !lineChartInstance) {
            const lineChartCtx = lineChartCanvasElement.getContext('2d');
            lineChartInstance = new Chart(lineChartCtx, {
                type: 'line',
                data: { labels: [], datasets: [{ data: [] }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(200, 200, 200, 0.2)' }, ticks: { color: textColorMuted } },
                        x: { grid: { display: false }, ticks: { color: textColorMuted } }
                    },
                    plugins: { legend: { display: true, position: 'top', labels: { color: textColorMuted } } }
                }
            });

            const initiallyActiveButton = document.querySelector('.header-filters button.active');
            const initialPeriod = initiallyActiveButton ? initiallyActiveButton.dataset.period : '7days';
            updateLineChart(initialPeriod);
        }

        const donutChartCanvasElement = document.getElementById('donutChartCanvas');
        if (donutChartCanvasElement && !donutChartInstance) {
            const donutChartCtx = donutChartCanvasElement.getContext('2d');
            donutChartInstance = new Chart(donutChartCtx, {
                type: 'doughnut',
                data: {
                    labels: ['CPU', 'Graphics', 'Page Head', 'Checkpoint', 'Other'],
                    datasets: [{
                        label: 'Top 5 Metrics',
                        data: [45, 25, 15, 8, 7],
                        backgroundColor: ['#7a5af5', '#b8aafb', '#d6d1fc', '#e8e6fd', '#f4f3fe'],
                        borderColor: '#fff', borderWidth: 2, hoverOffset: 8
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false, cutout: '70%',
                    plugins: { legend: { display: false } }
                }
            });
        }
    }

    function updateLineChart(period) {
        if (!lineChartInstance) return;

        function generateLineChartData(p) {
            let labels = [], data = [], numPoints = 0;
            switch (p) {
                case '24hours': numPoints = 24; for (let i = 0; i < numPoints; i++) labels.push(`${i}:00`); break;
                case '7days': numPoints = 7; const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']; const today = new Date().getDay(); for (let i = 0; i < numPoints; i++) { labels.push(days[(today - (numPoints - 1 - i) + 7) % 7]); } break;
                case '12months': numPoints = 12; labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']; break;
                default: numPoints = 28; for (let i = 1; i <= numPoints; i++) labels.push(`Day ${i}`); break;
            }
            for (let i = 0; i < numPoints; i++) data.push(Math.floor(Math.random() * 100) + 10);
            return { labels, data };
        }

        const { labels, data } = generateLineChartData(period);
        lineChartInstance.data.labels = labels;
        lineChartInstance.data.datasets[0] = {
            label: 'Anomalies Detected',
            data: data,
            borderColor: primaryColor,
            backgroundColor: 'rgba(122, 90, 245, 0.1)',
            tension: 0.4,
            fill: true,
            pointBackgroundColor: primaryColor,
            pointBorderColor: '#fff',
        };
        lineChartInstance.update();
    }

    const filterButtons = document.querySelectorAll('.header-filters button');
    filterButtons.forEach(button => {
        button.addEventListener('click', function () {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            updateLineChart(this.dataset.period);
        });
    });

    // --- Initial Load ---
    renderFileSystem();
});