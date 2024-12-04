document.addEventListener('DOMContentLoaded', function () {
    const textModal = document.getElementById('textModal');
    const qrModal = document.getElementById('qrModal');
    const historyModal = document.getElementById('historyModal');

    document.querySelectorAll('.config-button').forEach(button => {
        if (button.textContent.trim() === 'TEXT') {
            button.addEventListener('click', function (e) {
                const card = e.target.closest('.config-card');
                const config = getConfigDetails(card);
                showTextModal(config);
            });
        } else if (button.textContent.trim() === 'QR') {
            button.addEventListener('click', function (e) {
                const card = e.target.closest('.config-card');
                const config = getConfigDetails(card);
                showQRModal(config);
            });
        } else if (button.textContent.trim() === 'FILE') {
            button.addEventListener('click', function (e) {
                const card = e.target.closest('.config-card');
                const config = getConfigDetails(card);
                downloadConfig(config);
            });
        }
    });

    const freezeButton = document.querySelector('.action-button.freeze');
    const newConfigButton = document.querySelector('.action-button.new-config');
    const addFundsButton = document.querySelector('.action-button.add-funds');

    const freezeModal = document.getElementById('freezeModal');
    const configCreatedModal = document.getElementById('configCreatedModal');
    const addFundsModal = document.getElementById('addFundsModal');

    freezeButton.addEventListener('click', () => {
        freezeModal.style.display = 'flex';
    });

    freezeModal.querySelector('.confirm').addEventListener('click', () => {
        freezeModal.style.display = 'none';
    });

    newConfigButton.addEventListener('click', () => {
        configCreatedModal.style.display = 'flex';
    });

    addFundsButton.addEventListener('click', () => {
        addFundsModal.style.display = 'flex';
    });

    addFundsModal.querySelector('.confirm').addEventListener('click', () => {
        const amount = document.getElementById('fundsAmount').value;
        if (amount && amount > 0) {
            addFundsModal.style.display = 'none';
        }
    });

    document.querySelectorAll('.modal-button.cancel').forEach(button => {
        button.addEventListener('click', (e) => {
            e.target.closest('.modal-overlay').style.display = 'none';
        });
    });

    document.querySelectorAll('.modal-button.confirm:not(.warning)').forEach(button => {
        button.addEventListener('click', (e) => {
            if (!e.target.closest('#freezeModal')) {
                e.target.closest('.modal-overlay').style.display = 'none';
            }
        });
    });

    document.querySelectorAll('.modal-close').forEach(button => {
        button.addEventListener('click', (e) => {
            e.target.closest('.modal-overlay').style.display = 'none';
        });
    });

    const historyButton = document.querySelector('.history-button');
    historyButton.addEventListener('click', () => {
        historyModal.style.display = 'flex';
    });

    const notificationsToggle = document.querySelector('.notifications-toggle');
    const notificationsPanel = document.querySelector('.notifications-panel');
    const notificationsBadge = document.querySelector('.notifications-badge');

    // Initially hide the panel
    notificationsPanel.classList.remove('show');

    notificationsToggle.addEventListener('click', () => {
        notificationsPanel.classList.toggle('show');
        notificationsToggle.classList.remove('has-notifications');
    });

    // Add notification handling
    document.querySelectorAll('.notification-close').forEach(button => {
        button.addEventListener('click', (event) => {
            const notification = event.target.closest('.notification-item');
            const notificationId = notification.getAttribute('data-id'); // Получаем ID уведомления

            notification.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                notification.remove();
                updateNotificationCount();
            }, 300);
            event.stopPropagation();


            event.preventDefault();

            fetch('/vpn/profile/close_notification', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ id: notificationId }) // Отправляем ID в теле запроса
            })
                .then(response => {
                    if (response.status === 200) {
                        console.log('Уведомление удалено');
                    }
                    else {
                        console.error('Ошибка при удалении уведомления');
                    }
                })
                .catch(error => {
                    console.error('Ошибка сети:', error);
                });
        });
    });

    function updateNotificationCount() {
        const count = document.querySelectorAll('.notification-item').length;
        const countElement = document.querySelector('.notification-count');
        notificationsBadge.textContent = count;
        countElement.textContent = count;

        if (count === 0) {
            notificationsPanel.classList.remove('show');
            notificationsToggle.style.display = 'none';
        } else {
            notificationsToggle.classList.add('has-notifications');
        }
    }

    // Initial call to set up notification count
    updateNotificationCount();

    function getConfigDetails(card) {
        // const name = card.querySelector('.config-name').textContent;
        const details = Array.from(card.querySelectorAll('.config-detail')).map(detail => {
            const label = detail.querySelector('.detail-label').textContent;
            const value = detail.querySelector('span:last-child').textContent;
            return `${label} = ${value}`;
        }).join('\n');
        const extra = Array.from(card.querySelectorAll('.config-extra')).map(detail => {
            const label = detail.querySelector('.extra-label').textContent;
            const value = detail.querySelector('span:last-child').textContent;
            return `${label} = ${value}`;
        }).join('\n');
        return `[Interface]\n${details}\n[Peer]\n${extra}`;
    }

    function showTextModal(config) {
        const configText = textModal.querySelector('.config-text');
        configText.textContent = config;
        textModal.style.display = 'flex';

        const copyButton = textModal.querySelector('.copy-button');
        copyButton.addEventListener('click', () => {
            navigator.clipboard.writeText(config).then(() => {
                copyButton.textContent = 'Copied!';
                setTimeout(() => {
                    copyButton.textContent = 'Copy Configuration';
                }, 2000);
            });
        });
    }

    function showQRModal(config) {
        const qrContainer = qrModal.querySelector('.qr-code');
        qrContainer.innerHTML = '';
        new QRCode(qrContainer, {
            text: config,
            width: 256,
            height: 256,
            colorDark: "#FFFFFF",
            colorLight: "#000000",
        });
        qrModal.style.display = 'flex';
    }

    function downloadConfig(config) {
        const blob = new Blob([config], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'myVpn.conf';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
});