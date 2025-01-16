const canvas = document.getElementById('fireworks');
const ctx = canvas.getContext('2d');

// 设置canvas尺寸为窗口大小
function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}

// 监听窗口大小变化
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// 烟花粒子类
class Particle {
    constructor(x, y, color) {
        this.x = x;
        this.y = y;
        this.color = color;
        this.velocity = {
            x: (Math.random() - 0.5) * 8,
            y: (Math.random() - 0.5) * 8
        };
        this.alpha = 1;
        this.friction = 0.95;
    }

    draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${this.color}, ${this.alpha})`;
        ctx.fill();
    }

    update() {
        this.velocity.x *= this.friction;
        this.velocity.y *= this.friction;
        this.x += this.velocity.x;
        this.y += this.velocity.y;
        this.alpha -= 0.01;
    }
}

// 存储所有粒子
let particles = [];

// 创建烟花
function createFirework(x, y) {
    const colors = [
        '255, 0, 0',    // 红
        '0, 255, 0',    // 绿
        '0, 0, 255',    // 蓝
        '255, 255, 0',  // 黄
        '255, 0, 255',  // 紫
        '0, 255, 255',  // 青
        '255, 165, 0',  // 橙
        '255, 192, 203' // 粉
    ];
    
    // 为每个粒子随机选择颜色
    for (let i = 0; i < 50; i++) {
        const color = colors[Math.floor(Math.random() * colors.length)];
        particles.push(new Particle(x, y, color));
    }
}

// 点击创建烟花
canvas.addEventListener('click', (e) => {
    createFirework(e.clientX, e.clientY);
});

// 动画循环
function animate() {
    requestAnimationFrame(animate);
    ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    particles = particles.filter(particle => particle.alpha > 0);
    particles.forEach(particle => {
        particle.update();
        particle.draw();
    });
}

animate();

// 自动生成烟花
setInterval(() => {
    createFirework(
        Math.random() * canvas.width,
        Math.random() * canvas.height
    );
}, 2000); 