/*
视差效果的实现原理：
通过鼠标的移动来设置对应元素的位置来实现视差效果。
本示例中使用的五个data属性值：
  data-speedx：设置元素在X轴方向上的移动速度
  data-speedy：设置元素在Y轴方向上的移动速度
  data-speedz：设置元素在Z轴方向上的移动速度
  data-rotation：设置元素绕Y轴旋转的速度
  data-distance：设置元素距离视点的距离
  上述值的设定依据是：近小远大
GSAP实现的是位移动画，不参与视差效果的显示
*/

// 获取视差显示的元素
const parallax_els = document.querySelectorAll(".parallax");

let xValue = 0,
  yValue = 0;

let rotateDegree = 0;

function update(cursorPosition) {
  parallax_els.forEach((el) => {
    // 获取参数
    let speedx = el.dataset.speedx;
    let speedy = el.dataset.speedy;
    let speedz = el.dataset.speedz;
    let rotateSpeed = el.dataset.rotation;

    // 判断是否在左侧
    // 原理：元素的左侧值小于窗口宽度的一半，则元素在左侧，反之在右侧
    let isInLeft =
      parseFloat(getComputedStyle(el).left) < window.innerWidth / 2 ? 1 : -1;
    // 计算Z轴偏移量
    let zValue =
      (cursorPosition - parseFloat(getComputedStyle(el).left)) * isInLeft * 0.1;
    // 设置元素的样式
    el.style.transform = `perspective(2300px) translateZ(${
      zValue * speedz
    }px) rotateY(${rotateDegree * rotateSpeed}deg) translateX(calc(-50% + ${
      -xValue * speedx
    }px)) translateY(calc(-50% + ${yValue * speedy}px)) `;
  });
}

update(0);

window.addEventListener("mousemove", (e) => {
  // 确保timeline执行完之前不处理鼠标移动操作
  if (timeline.isActive()) {
    return;
  }

  xValue = e.clientX - window.innerWidth / 2;
  yValue = e.clientY - window.innerHeight / 2;

  rotateDegree = (xValue / (window.innerWidth / 2)) * 20;

  update(e.clientX);
});

// GSAP 动画
// 创建timeline
let timeline = gsap.timeline();

// 设置非文字动画
Array.from(parallax_els)
  .filter((el) => !el.classList.contains("text"))
  .forEach((el) => {
    timeline.from(
      el,
      {
        top: `${el.offsetHeight / 2 + +el.dataset.distance}px`,
        duration: 3.5,
        ease: "power3.out",
      },
      "1"
    );
  });

// 设置文字动画
timeline.from(
  ".text h1",
  {
    y:
      window.innerHeight -
      document.querySelector(".text h1").getBoundingClientRect().top +
      200,
    duration: 2,
  },
  "2.5"
);

timeline.from(
  ".text h2",
  {
    y: -150,
    opacity: 0,
    duration: 1.5,
  },
  "3"
);

// 设置有hide属性的元素的动画
timeline.from(".hide", { opacity: 0, duration: 1.5 }, "3");
