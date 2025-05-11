document.addEventListener('DOMContentLoaded', function () {
    const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim();
    const textColorMuted = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim();

    // --- Line Chart ---
    const lineChartCanvasElement = document.getElementById('lineChartCanvas');
    let lineChartInstance;

    if (lineChartCanvasElement) { // Kiểm tra xem canvas có tồn tại không
        const lineChartCtx = lineChartCanvasElement.getContext('2d');
        const lineChartDataTemplate = {
            labels: [],
            datasets: [{
                label: 'Anomalies Detected',
                data: [],
                borderColor: primaryColor,
                backgroundColor: 'rgba(122, 90, 245, 0.1)', // Light primary color fill
                tension: 0.4,
                fill: true,
                pointBackgroundColor: primaryColor,
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: primaryColor
            }]
        };

        function generateLineChartData(period) {
            let labels = [];
            let data = [];
            let numPoints = 0;

            switch (period) {
                case '24hours':
                    numPoints = 24;
                    for (let i = 0; i < numPoints; i++) labels.push(`${i}:00`);
                    break;
                case '7days':
                    numPoints = 7;
                    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                    const today = new Date().getDay(); // 0 for Sun, 1 for Mon ...
                    for (let i = 0; i < numPoints; i++) {
                        labels.push(days[(today - (numPoints - 1 - i) + 7) % 7]);
                    }
                    break;
                case '28days':
                    numPoints = 28;
                    for (let i = 1; i <= numPoints; i++) labels.push(`Day ${i}`);
                    break;
                case '12months':
                    numPoints = 12;
                    labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                    break;
                default:
                    numPoints = 7; // Default to 7 days
                    for (let i = 1; i <= numPoints; i++) labels.push(`Day ${i}`);
            }

            for (let i = 0; i < numPoints; i++) {
                data.push(Math.floor(Math.random() * 100) + 10); // Random data
            }
            return { labels, data };
        }

        function updateLineChart(period) {
            const { labels, data } = generateLineChartData(period);
            if (lineChartInstance) {
                lineChartInstance.data.labels = labels;
                lineChartInstance.data.datasets[0].data = data;
                lineChartInstance.update();
            } else {
                const initialData = JSON.parse(JSON.stringify(lineChartDataTemplate)); // Deep clone
                initialData.labels = labels;
                initialData.datasets[0].data = data;
                lineChartInstance = new Chart(lineChartCtx, {
                    type: 'line',
                    data: initialData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: {
                                    color: 'rgba(200, 200, 200, 0.2)' // Lighter grid lines
                                },
                                ticks: { color: textColorMuted }
                            },
                            x: {
                                grid: {
                                    display: false // Hide x-axis grid lines
                                },
                                ticks: { color: textColorMuted }
                            }
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top',
                                labels: { color: textColorMuted }
                            },
                            tooltip: {
                                backgroundColor: '#fff',
                                titleColor: '#333',
                                bodyColor: '#333',
                                borderColor: primaryColor,
                                borderWidth: 1,
                                padding: 10,
                                callbacks: {
                                    label: function(context) {
                                        let label = context.dataset.label || '';
                                        if (label) {
                                            label += ': ';
                                        }
                                        if (context.parsed.y !== null) {
                                            label += context.parsed.y;
                                        }
                                        return label;
                                    }
                                }
                            }
                        }
                    }
                });
            }
        }

        // Filter buttons interaction
        const filterButtons = document.querySelectorAll('.header-filters button');
        filterButtons.forEach(button => {
            button.addEventListener('click', function () {
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                const period = this.dataset.period;
                updateLineChart(period);
            });
        });

        // Initial load for line chart (default to '7days')
        const initiallyActiveButton = document.querySelector('.header-filters button.active');
        const initialPeriod = initiallyActiveButton ? initiallyActiveButton.dataset.period : '7days';
        updateLineChart(initialPeriod);
    }


    // --- Donut Chart ---
    const donutChartCanvasElement = document.getElementById('donutChartCanvas');

    if (donutChartCanvasElement) { // Kiểm tra xem canvas có tồn tại không
        const donutChartCtx = donutChartCanvasElement.getContext('2d');
        const donutChartData = {
            labels: ['CPU', 'Graphics', 'Page Head', 'Checkpoint', 'Other'],
            datasets: [{
                label: 'Top 5 Metrics',
                data: [45, 25, 15, 8, 7], // Sample data
                backgroundColor: [ // Match these with your static legend in HTML
                    '#7a5af5',
                    '#b8aafb',
                    '#d6d1fc',
                    '#e8e6fd',
                    '#f4f3fe'
                ],
                borderColor: '#fff', // White border for segments
                borderWidth: 2,
                hoverOffset: 8,
                hoverBorderColor: primaryColor // Highlight border on hover
            }]
        };

        new Chart(donutChartCtx, {
            type: 'doughnut',
            data: donutChartData,
            options: {
                responsive: true,
                maintainAspectRatio: false, // Allow it to fill container better
                cutout: '70%', // Makes it a doughnut, adjust for thickness
                plugins: {
                    legend: {
                        display: false // Hide Chart.js legend as we have a static HTML one
                    },
                    tooltip: {
                            backgroundColor: '#fff',
                        titleColor: '#333',
                        bodyColor: '#333',
                        borderColor: primaryColor,
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed !== null) {
                                    label += context.parsed + '%'; // Assuming data is in percentage
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
});