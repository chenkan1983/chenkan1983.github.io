import {
    simulationVertexShader,
    simulationFragmentShader,
    renderVertexShader,
    renderFragmentShader
} from './water_shader.js'

document.addEventListener('DOMContentLoaded', () => {
    const scene = new THREE.Scene()
    const simScene = new THREE.Scene()
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)
    const renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        preserveDrawingBuffer: true,
    })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    
    renderer.setSize(window.innerWidth, window.innerHeight);
    
    document.body.appendChild(renderer.domElement);

    const mouse = new THREE.Vector2();
    let frame = 0;
    const width = window.innerWidth * window.devicePixelRatio;
    const height = window.innerHeight * window.devicePixelRatio;

    const options = {
        format: THREE.RGBAFormat,
        type: THREE.FloatType,
        minFilter: THREE.LinearFilter,
        magFilter: THREE.LinearFilter,
        stencilBuffer: false,
        depthBuffer: false,
    }
    let rtA = new THREE.WebGLRenderTarget(width, height, options);
    let rtB = new THREE.WebGLRenderTarget(width, height, options);

    const simMaterial = new THREE.ShaderMaterial({
        uniforms: {
            textureA: { value: null },
            mouse: { value: mouse },
            resolution: { value: new THREE.Vector2(width, height) },
            time: { value: 0 },
            frame: { value: 0 },
        },
        vertexShader: simulationVertexShader,
        fragmentShader: simulationFragmentShader
    });
    
    const rendenMaterial = new THREE.ShaderMaterial({
        uniforms: {
            textureA: { value: null },
            textureB: { value: null },
            resolution: { value: new THREE.Vector2(width, height) },
        },
        vertexShader: renderVertexShader,
        fragmentShader: renderFragmentShader,
        transparent: true,
    })
    
    const plane = new THREE.PlaneGeometry(2, 2);
    const simQuad = new THREE.Mesh(plane, simMaterial);
    const renderQuad = new THREE.Mesh(plane, rendenMaterial);
    
    simScene.add(simQuad);
    scene.add(renderQuad);
    
    
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    
    const ctx = canvas.getContext('2d', { alpha: true });
    ctx.fillStyle = '#fb7427';
    ctx.fillRect(0, 0, width, height);
    
    const fontSize = Math.round(250 * window.devicePixelRatio);
    ctx.fillStyle = '#fef4b8';
    ctx.font = `bold ${fontSize}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.textRendering = 'geometricPrecision';
    ctx.imageSmoothingEnabled = true;
    ctx.fillText('softhorizon', width / 2, height / 2);
    
    const textTexture = new THREE.CanvasTexture(canvas);
    textTexture.minFilter = THREE.LinearFilter;
    textTexture.magFilter = THREE.LinearFilter;
    textTexture.format = THREE.RGBAFormat;
    
    window.addEventListener("resize", () => {
        const newWidth = window.innerWidth * window.devicePixelRatio;
        const newHeight = window.innerHeight * window.devicePixelRatio;
        
        canvas.width = newWidth;
        canvas.height = newHeight;
        
        ctx.fillStyle = '#fb7427';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const newFontSize = Math.round(250 * window.devicePixelRatio);
        ctx.fillStyle = '#fef4b8';
        ctx.font = `bold ${newFontSize}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('softhorizon', canvas.width / 2, canvas.height / 2);
        textTexture.needsUpdate = true;
    })
    
    renderer.domElement.addEventListener('mousemove', (e) => {
        mouse.x = e.clientX * window.devicePixelRatio;
        mouse.y = (window.innerHeight - e.clientY) * window.devicePixelRatio;
    })
    renderer.domElement.addEventListener('mouseleave', () => {
        mouse.set(0, 0);
    })
    
    const animate = () => {
        simMaterial.uniforms.frame.value = frame++;
        simMaterial.uniforms.time.value = performance.now() / 1000;
        simMaterial.uniforms.textureA.value = rtA.texture;
    
        renderer.setRenderTarget(rtB);
        renderer.render(simScene, camera);
    
        rendenMaterial.uniforms.textureA.value = rtB.texture;
        rendenMaterial.uniforms.textureB.value = textTexture;
    
        renderer.setRenderTarget(null);
        renderer.render(scene, camera);
    
        const temp = rtA;
        rtA = rtB;
        rtB = temp;
    
        requestAnimationFrame(animate);
    }
    animate();
})
