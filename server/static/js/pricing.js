
const planDetails = {
    'Пробный': {
        description: 'Perfect for testing our service. Experience basic VPN features with limited server access.',
        features: {
            'Basic VPN Features': 'Access to essential VPN security features and protocols',
            '3 Server Locations': 'Connect to servers in 3 strategic locations',
            'Standard Speed': 'Reliable connection speeds for regular browsing',
            '1 Device': 'VPN protection for a single device'
        }
    },
    'Базовый': {
        description: 'Great for individual users who need reliable VPN protection with more flexibility.',
        features: {
            'All VPN Features': 'Full access to all VPN security features and protocols',
            '10 Server Locations': 'Connect to servers in 10 different countries',
            'High Speed': 'Enhanced connection speeds for streaming and downloads',
            '3 Devices': 'Protect up to 3 devices simultaneously'
        }
    },
    'Расширенный': {
        description: 'Our most popular plan, perfect for families or users with multiple devices.',
        features: {
            'All VPN Features': 'Complete access to premium VPN features',
            'All Server Locations': 'Unlimited access to our global server network',
            'Ultra-fast Speed': 'Optimized speeds for gaming and HD streaming',
            '5 Devices': 'Protection for up to 5 devices',
            'Priority Support': 'Fast response times from our support team'
        }
    },
    'Люкс': {
        description: 'Ultimate protection and freedom with no limitations.',
        features: {
            'All VPN Features': 'Premium access to all current and future features',
            'All Server Locations': 'Premium server access with optimized routing',
            'Ultra-fast Speed': 'The fastest speeds we offer with no throttling',
            'Unlimited Devices': 'No device limit - protect your whole network',
            '24/7 Priority Support': 'Round-the-clock dedicated support',
            'Dedicated IP': 'Your own private IP address'
        }
    }
};

document.querySelectorAll('.pricing-card').forEach(card => {
    card.addEventListener('click', (e) => {
        if (e.target.classList.contains('cta-button')) return;

        const planName = card.querySelector('h3').textContent;
        const plan = planDetails[planName];

        const modal = document.getElementById('modal');
        const modalTitle = modal.querySelector('.modal-title');
        const modalDescription = modal.querySelector('.modal-description');
        const modalFeatures = modal.querySelector('.modal-features');

        modalTitle.textContent = planName + ' тариф';
        modalDescription.textContent = plan.description;

        modalFeatures.innerHTML = Object.entries(plan.features)
            .map(([feature, detail]) => `
    <div class="feature-detail">
        <svg width="20" height="20" viewBox="0 0 20 20">
            <path d="M8.43 14.43L3.85 9.85L5.27 8.43L8.43 11.59L14.73 5.29L16.15 6.71L8.43 14.43Z"/>
        </svg>
    <div>
        <strong>${feature}:</strong> ${detail}
        </div>
    </div>
    `).join('');

        modal.classList.add('active');
    });
});

document.querySelector('.close-modal').addEventListener('click', () => {
    document.getElementById('modal').classList.remove('active');
});

document.getElementById('modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
        e.target.classList.remove('active');
    }
});
