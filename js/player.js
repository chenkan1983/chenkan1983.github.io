document.addEventListener('DOMContentLoaded', function() {
    const startButton = document.getElementById('startButton');
    const videoPlayer = document.getElementById('videoPlayer');
    const leftContent = document.querySelector('.left-content');
    const rightContent = document.querySelector('.right-content');
    const initialContent = document.querySelector('.initial-content');
    const endingContent = document.querySelector('.ending-content');
    const backgroundMusic = document.getElementById('backgroundMusic');
    let isPlaying = false;
    let timer = null;

    // 切换到结束内容
    function switchToEnding() {
        // 添加淡出效果
        videoPlayer.style.opacity = '0';
        videoPlayer.style.transition = 'opacity 2s linear';
        rightContent.style.opacity = '0';
        rightContent.style.transition = 'opacity 2s linear';
        
        setTimeout(() => {
            videoPlayer.style.display = 'none';
            rightContent.style.display = 'none';
            rightContent.classList.remove('active');
            startButton.style.display = 'none';
            
            initialContent.classList.remove('active');
            initialContent.classList.add('fade-out');
            
            leftContent.classList.add('active');
            
            endingContent.style.display = 'flex';
            endingContent.offsetHeight;
            
            requestAnimationFrame(() => {
                endingContent.classList.add('fade-in');
                endingContent.classList.add('fullscreen');
            });

            // 创建canvas元素
            const canvas = document.createElement('canvas');
            canvas.id = 'canvas';
            canvas.style.position = 'fixed';
            canvas.style.top = '0';
            canvas.style.left = '0';
            canvas.style.width = '100%';
            canvas.style.height = '100%';
            canvas.style.zIndex = '1000';
            canvas.style.pointerEvents = 'none';
            document.body.appendChild(canvas);

            // 初始化烟花效果
            const fireworks = new Fireworks();
            fireworks.init();

            // 添加窗口大小改变时的处理
            window.addEventListener('resize', () => {
                if (fireworks.canvas) {
                    fireworks.canvas.width = window.innerWidth;
                    fireworks.canvas.height = window.innerHeight;
                    fireworks.cx = fireworks.canvas.width / 2;
                    fireworks.cy = fireworks.canvas.height / 2;
                }
            });
        }, 500);
    }

    // 点击按钮处理
    startButton.addEventListener('click', function() {
        if (!isPlaying) {
            // 先播放背景音乐
            backgroundMusic.play();
            
            // 设置播放状态
            isPlaying = true;
            // startButton.textContent = '停止播放';
            startButton.style.display = 'none';
            
            // 3秒后开始播放视频和触发所有变化
            setTimeout(() => {
                // 先添加 initial-content 的 active 类，触发移动动画
                
                leftContent.classList.add('active');
                initialContent.classList.add('active');
                // 稍微延迟添加其他类，避免动画冲突
                rightContent.classList.add('active');
                    
                // 显示并播放视频
                videoPlayer.classList.add('show');
                setTimeout(() => {
                    videoPlayer.play();
                }, 1000);
                    
                 // 设置视频结束后切换到结束内容
                timer = setTimeout(switchToEnding, 100000);
            }, 3000);
            
        } 
    });


    // 设置背景音乐音量和循环
    backgroundMusic.volume = 0.1;
    backgroundMusic.loop = true;

    // 尝试自动播放背景音乐
    backgroundMusic.play().catch(function(error) {
        console.log("自动播放失败，需要用户交互才能播放音频:", error);
    });

    // 添加键盘事件监听
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' || event.keyCode === 13) {
            startButton.click();
        }
    });

    class Fireworks {
        constructor() {
            this.pi = Math.PI;
            this.canvas = null;
            this.ctx = null;
            this.cx = 0;
            this.cy = 0;
            this.playerX = 0;
            this.playerY = 0;
            this.playerZ = -100;
            this.scale = 1200;
            this.seedTimer = 0;
            this.seedInterval = 3;
            this.seedLife = 100;
            this.gravity = 0.02;
            this.seeds = [];
            this.sparkPics = [];
            this.sparks = [];
            this.frames = 0;
            this.s = "./assets/";
            this.pitch = 0;
            this.yaw = 0;
            this.showFlash = false;
            this.audioPool = [];
            this.audioLoaded = false;
        }

        init() {
            this.canvas = document.querySelector("#canvas");
            this.ctx = this.canvas.getContext("2d");
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
            this.cx = this.canvas.width / 2;
            this.cy = this.canvas.height / 2;

            let loadedImages = 0;
            for (let i = 1; i <= 11; i++) {
                const sparkPic = new Image();
                sparkPic.onload = () => {
                    loadedImages++;
                    if (loadedImages === 11) {
                        this.frame();
                    }
                };
                sparkPic.src = this.s + "images/spark" + i + ".png";
                this.sparkPics.push(sparkPic);
            }

            this.preloadAudio();
        }

        preloadAudio() {
            const audioFiles = ['pow1.mp3', 'pow2.mp3', 'pow3.mp3', 'pow4.mp3'];
            let loadedCount = 0;

            audioFiles.forEach((file, index) => {
                const audio = new Audio(this.s + "audio/" + file);
                audio.preload = 'auto';
                
                audio.addEventListener('canplaythrough', () => {
                    loadedCount++;
                    if (loadedCount === audioFiles.length) {
                        this.audioLoaded = true;
                    }
                });

                // 创建多个副本以支持同时播放
                for (let i = 0; i < 3; i++) {
                    const audioClone = audio.cloneNode();
                    this.audioPool.push(audioClone);
                }
            });
        }

        rasterizePoint(x, y, z) {
            var p, d
            x -= this.playerX
            y -= this.playerY
            z -= this.playerZ
            p = Math.atan2(x, z)
            d = Math.sqrt(x * x + z * z)
            x = Math.sin(p - this.yaw) * d
            z = Math.cos(p - this.yaw) * d
            p = Math.atan2(y, z)
            d = Math.sqrt(y * y + z * z)
            y = Math.sin(p - this.pitch) * d
            z = Math.cos(p - this.pitch) * d
            var rx1 = -1000,
                ry1 = 1,
                rx2 = 1000,
                ry2 = 1,
                rx3 = 0,
                ry3 = 0,
                rx4 = x,
                ry4 = z,
                uc = (ry4 - ry3) * (rx2 - rx1) - (rx4 - rx3) * (ry2 - ry1)
            if (!uc) return { x: 0, y: 0, d: -1 }
            var ua = ((rx4 - rx3) * (ry1 - ry3) - (ry4 - ry3) * (rx1 - rx3)) / uc
            var ub = ((rx2 - rx1) * (ry1 - ry3) - (ry2 - ry1) * (rx1 - rx3)) / uc
            if (!z) z = 0.000000001
            if (ua > 0 && ua < 1 && ub > 0 && ub < 1) {
                return {
                    x: this.cx + (rx1 + ua * (rx2 - rx1)) * this.scale,
                    y: this.cy + (y / z) * this.scale,
                    d: Math.sqrt(x * x + y * y + z * z),
                }
            } else {
                return {
                    x: this.cx + (rx1 + ua * (rx2 - rx1)) * this.scale,
                    y: this.cy + (y / z) * this.scale,
                    d: -1,
                }
            }
        }
        spawnSeed() {
            var seed = new Object()
            seed.x = -200 + Math.random() * 400
            seed.y = -50 + Math.random() * 150
            seed.z = 50 + Math.random() * 200
            seed.vx = 0.1 - Math.random() * 0.2
            seed.vy = -1.5 - Math.random() * 0.5
            seed.vz = 0.1 - Math.random() * 0.2
            seed.born = this.frames
            this.seeds.push(seed)
        }
        splode(x, y, z) {
            var t = 20 + parseInt(Math.random() * 280)
            var sparkV = 2 + Math.random() * 3.5
            var type = parseInt(Math.random() * 3)
            var pic1, pic2, pic3
            switch (type) {
                case 0:
                    pic1 = parseInt(Math.random() * 11)
                    break
                case 1:
                    pic1 = parseInt(Math.random() * 11)
                    do {
                        pic2 = parseInt(Math.random() * 11)
                    } while (pic2 == pic1)
                    break
                case 2:
                    pic1 = parseInt(Math.random() * 11)
                    do {
                        pic2 = parseInt(Math.random() * 11)
                    } while (pic2 == pic1)
                    do {
                        pic3 = parseInt(Math.random() * 11)
                    } while (pic3 == pic1 || pic3 == pic2)
                    break
            }
            for (var m = 1; m < t; ++m) {
                var spark = new Object()
                spark.x = x
                spark.y = y
                spark.z = z
                var p1 = this.pi * 2 * Math.random()
                var p2 = this.pi * Math.random()
                var v = sparkV * (1 + Math.random() / 6)
                spark.vx = Math.sin(p1) * Math.sin(p2) * v
                spark.vz = Math.cos(p1) * Math.sin(p2) * v
                spark.vy = Math.cos(p2) * v
                switch (type) {
                    case 0:
                        spark.img = this.sparkPics[pic1]
                        break
                    case 1:
                        spark.img = this.sparkPics[
                            parseInt(Math.random() * 2) ? pic1 : pic2
                        ]
                        break
                    case 2:
                        switch (parseInt(Math.random() * 3)) {
                            case 0:
                                spark.img = this.sparkPics[pic1]
                                break
                            case 1:
                                spark.img = this.sparkPics[pic2]
                                break
                            case 2:
                                spark.img = this.sparkPics[pic3]
                                break
                        }
                        break
                }
                spark.radius = 35 + Math.random() * 60
                spark.alpha = 1
                spark.trail = new Array()
                this.sparks.push(spark)
            }
            if (this.audioLoaded) {
                // 从音频池中获取一个可用的音频实例
                const pow = this.audioPool.find(audio => audio.paused);
                if (pow) {
                    var d = Math.sqrt(
                        (x - this.playerX) * (x - this.playerX) +
                        (y - this.playerY) * (y - this.playerY) +
                        (z - this.playerZ) * (z - this.playerZ)
                    );
                    var yDistance = Math.abs(y - this.playerY) / 100;
                    var zDistance = Math.abs(z) / 200;
                    var volume = 1.5 / (1 + d/11 + yDistance + zDistance);
                    volume = Math.max(0.1, Math.min(1.0, volume));
                    pow.volume = volume;
                    pow.currentTime = 0;
                    pow.play().catch(e => console.log('播放失败:', e));
                }
            }
        }

        doLogic() {
            var x, y, z
            if (this.seedTimer < this.frames) {
                this.seedTimer = this.frames + this.seedInterval * Math.random() * 10
                this.spawnSeed()
            }
            for (var i = 0; i < this.seeds.length; ++i) {
                this.seeds[i].vy += this.gravity
                this.seeds[i].x += this.seeds[i].vx
                this.seeds[i].y += this.seeds[i].vy
                this.seeds[i].z += this.seeds[i].vz
                if (this.frames - this.seeds[i].born > this.seedLife) {
                    this.splode(this.seeds[i].x, this.seeds[i].y, this.seeds[i].z)
                    this.seeds.splice(i, 1)
                }
            }
            for (var i = 0; i < this.sparks.length; ++i) {
                if (this.sparks[i].alpha > 0 && this.sparks[i].radius > 5) {
                    this.sparks[i].alpha -= 0.01
                    this.sparks[i].radius /= 1.02
                    this.sparks[i].vy += this.gravity
                    var point = new Object()
                    point.x = this.sparks[i].x
                    point.y = this.sparks[i].y
                    point.z = this.sparks[i].z
                    if (this.sparks[i].trail.length) {
                        x = this.sparks[i].trail[this.sparks[i].trail.length - 1].x
                        y = this.sparks[i].trail[this.sparks[i].trail.length - 1].y
                        z = this.sparks[i].trail[this.sparks[i].trail.length - 1].z
                        var d =
                            (point.x - x) * (point.x - x) +
                            (point.y - y) * (point.y - y) +
                            (point.z - z) * (point.z - z)
                        if (d > 9) {
                            this.sparks[i].trail.push(point)
                        }
                    } else {
                        this.sparks[i].trail.push(point)
                    }
                    if (this.sparks[i].trail.length > 5)
                        this.sparks[i].trail.splice(0, 1)
                    this.sparks[i].x += this.sparks[i].vx
                    this.sparks[i].y += this.sparks[i].vy
                    this.sparks[i].z += this.sparks[i].vz
                    this.sparks[i].vx /= 1.05
                    this.sparks[i].vy /= 1.05
                    this.sparks[i].vz /= 1.05
                } else {
                    this.sparks.splice(i, 1)
                }
            }
        }
        rgb(col) {
            var r = parseInt((0.5 + Math.sin(col) * 0.5) * 16)
            var g = parseInt((0.5 + Math.cos(col) * 0.5) * 16)
            var b = parseInt((0.5 - Math.sin(col) * 0.5) * 16)
            return "#" + r.toString(16) + g.toString(16) + b.toString(16)
        }
        draw() {
            this.ctx.clearRect(0, 0, this.cx * 2, this.cy * 2)
            this.ctx.fillStyle = "#ffd"
            this.ctx.globalAlpha = 1
            var size
            var point
            for (var i = 0; i < this.seeds.length; ++i) {
                point = this.rasterizePoint(
                    this.seeds[i].x,
                    this.seeds[i].y,
                    this.seeds[i].z
                )
                if (point.d != -1) {
                    size = 200 / (1 + point.d)
                    this.ctx.fillRect(point.x - size / 2, point.y - size / 2, size, size)
                }
            }
            var point1 = new Object()
            var point2
            for (var i = 0; i < this.sparks.length; ++i) {
                point = this.rasterizePoint(
                    this.sparks[i].x,
                    this.sparks[i].y,
                    this.sparks[i].z
                )
                if (point.d != -1) {
                    size = (this.sparks[i].radius * 200) / (1 + point.d)
                    if (this.sparks[i].alpha < 0) this.sparks[i].alpha = 0
                    if (this.sparks[i].trail.length) {
                        point1.x = point.x
                        point1.y = point.y
                        switch (this.sparks[i].img) {
                            case this.sparkPics[0]:
                                this.ctx.strokeStyle = "#ff3300"
                                break
                            case this.sparkPics[1]:
                                this.ctx.strokeStyle = "#ff0066"
                                break
                            case this.sparkPics[2]:
                                this.ctx.strokeStyle = "#00ffcc"
                                break
                            case this.sparkPics[3]:
                                this.ctx.strokeStyle = "#ff1111"
                                break
                            case this.sparkPics[4]:
                                this.ctx.strokeStyle = "#ffcc00"
                                break
                            case this.sparkPics[5]:
                                this.ctx.strokeStyle = "#ff0000"
                                break
                            case this.sparkPics[6]:
                                this.ctx.strokeStyle = "#ff6600"
                                break
                            case this.sparkPics[7]:
                                this.ctx.strokeStyle = "#cc00ff"
                                break
                            case this.sparkPics[8]:
                                this.ctx.strokeStyle = "#ff3366"
                                break
                            case this.sparkPics[9]:
                                this.ctx.strokeStyle = "#ff9933"
                                break
                            case this.sparkPics[10]:
                                this.ctx.strokeStyle = "#ff00cc"
                                break
                        }
                        for (var j = this.sparks[i].trail.length - 1; j >= 0; --j) {
                            point2 = this.rasterizePoint(
                                this.sparks[i].trail[j].x,
                                this.sparks[i].trail[j].y,
                                this.sparks[i].trail[j].z
                            )
                            if (point2.d != -1) {
                                this.ctx.globalAlpha =
                                    ((j / this.sparks[i].trail.length) * this.sparks[i].alpha) * 0.7
                                this.ctx.beginPath()
                                this.ctx.moveTo(point1.x, point1.y)
                                this.ctx.lineWidth =
                                    2 +
                                    (this.sparks[i].radius * 12) /
                                    (this.sparks[i].trail.length - j) /
                                    (1 + point2.d)
                                this.ctx.lineTo(point2.x, point2.y)
                                this.ctx.stroke()
                                point1.x = point2.x
                                point1.y = point2.y
                            }
                        }
                    }
                    this.ctx.globalAlpha = this.sparks[i].alpha
                    this.ctx.drawImage(
                        this.sparks[i].img,
                        point.x - size / 2,
                        point.y - size / 2,
                        size,
                        size
                    )
                }
            }
        }
        frame() {
            if (this.frames > 100000) {
                this.seedTimer = 0;
                this.frames = 0;
            }
            this.frames++;
            this.draw();
            this.doLogic();
            requestAnimationFrame(() => this.frame());
        }
    }

}); 
