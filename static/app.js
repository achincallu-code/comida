document.addEventListener("DOMContentLoaded", () => {
  const money = value => new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN"
  }).format(value);

  document.querySelectorAll(".data-chart").forEach(canvas => {
    const data = JSON.parse(canvas.dataset.chart);
    const series = canvas.dataset.series;
    const values = data[series] || [];
    const labels = data.labels || [];
    const isCurrency = canvas.dataset.currency === "true";

    const draw = () => {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (!width || !height) return;

      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      const context = canvas.getContext("2d");
      context.scale(ratio, ratio);

      const left = 37;
      const right = width - 8;
      const top = 10;
      const bottom = height - 23;
      const plotWidth = right - left;
      const plotHeight = bottom - top;
      const maxValue = Math.max(...values, 0);
      const ceiling = maxValue === 0 ? 1 : maxValue * 1.18;

      context.font = "9px DM Sans, Arial, sans-serif";
      context.textAlign = "right";
      context.textBaseline = "middle";
      for (let tick = 0; tick <= 3; tick += 1) {
        const y = top + plotHeight * tick / 3;
        const value = ceiling * (3 - tick) / 3;
        context.beginPath();
        context.strokeStyle = "#2b2d27";
        context.lineWidth = 1;
        context.moveTo(left, y);
        context.lineTo(right, y);
        context.stroke();
        context.fillStyle = "#c3c5bd";
        context.fillText(
          isCurrency ? `$${Math.round(value)}` : String(Math.round(value)),
          left - 7,
          y
        );
      }

      if (!values.length) return;
      const points = values.map((value, index) => ({
        x: values.length === 1 ? left + plotWidth / 2 : left + plotWidth * index / (values.length - 1),
        y: bottom - plotHeight * value / ceiling,
        value
      }));
      const color = isCurrency ? "#73cb98" : "#ff7848";
      const fill = context.createLinearGradient(0, top, 0, bottom);
      fill.addColorStop(0, isCurrency ? "#73cb9833" : "#ff784833");
      fill.addColorStop(1, isCurrency ? "#73cb9800" : "#ff784800");

      context.beginPath();
      points.forEach((point, index) => {
        if (index === 0) context.moveTo(point.x, point.y);
        else {
          const previous = points[index - 1];
          const midpoint = (previous.x + point.x) / 2;
          context.bezierCurveTo(midpoint, previous.y, midpoint, point.y, point.x, point.y);
        }
      });
      context.lineTo(points[points.length - 1].x, bottom);
      context.lineTo(points[0].x, bottom);
      context.closePath();
      context.fillStyle = fill;
      context.fill();

      context.beginPath();
      points.forEach((point, index) => {
        if (index === 0) context.moveTo(point.x, point.y);
        else {
          const previous = points[index - 1];
          const midpoint = (previous.x + point.x) / 2;
          context.bezierCurveTo(midpoint, previous.y, midpoint, point.y, point.x, point.y);
        }
      });
      context.strokeStyle = color;
      context.lineWidth = 2;
      context.lineJoin = "round";
      context.lineCap = "round";
      context.stroke();

      points.forEach((point, index) => {
        context.beginPath();
        context.arc(point.x, point.y, 3, 0, Math.PI * 2);
        context.fillStyle = "#191a17";
        context.fill();
        context.strokeStyle = color;
        context.lineWidth = 1.7;
        context.stroke();
        const showLabel = labels.length <= 8 || index % 2 === 0 || index === labels.length - 1;
        if (showLabel) {
          context.fillStyle = "#c3c5bd";
          context.font = "8px DM Sans, Arial, sans-serif";
          context.textAlign = index === 0 ? "left" : index === labels.length - 1 ? "right" : "center";
          context.textBaseline = "top";
          context.fillText(labels[index], point.x, bottom + 9);
        }
      });
      canvas.title = points.map((point, index) =>
        `${labels[index]}: ${isCurrency ? money(point.value) : point.value + " pedidos"}`
      ).join(" · ");
    };

    draw();
    if ("ResizeObserver" in window) new ResizeObserver(draw).observe(canvas);
    else window.addEventListener("resize", draw);
  });

  const form = document.getElementById("orderForm");
  if (form) {
    const amount = document.getElementById("cantidad");
    const total = document.getElementById("total");
    const mobileTotal = document.getElementById("mobile-total");
    const client = form.querySelector('[name="cliente"]');
    const delivery = document.getElementById("entrega");
    const productPreview = document.getElementById("preview-product");
    const previewClient = document.getElementById("preview-client");
    const previewQuantity = document.getElementById("preview-quantity");
    const previewDelivery = document.getElementById("preview-delivery");
    const previewEmoji = document.getElementById("preview-emoji");
    const emojis = {
      "Hamburguesa clásica": "🍔",
      "Pizza individual": "🍕",
      "Tacos (orden)": "🌮",
      "Ensalada fresca": "🥗",
      "Papas a la francesa": "🍟",
      "Combo especial": "🍱"
    };

    const updatePreview = () => {
      const selected = form.querySelector('input[name="producto"]:checked');
      const count = Number(amount.value || 1);
      const subtotal = selected ? Number(selected.dataset.price) * count : 0;
      const formatted = money(subtotal);
      total.textContent = formatted;
      if (mobileTotal) mobileTotal.textContent = formatted;
      productPreview.textContent = selected ? selected.value : "Elige un platillo";
      previewEmoji.textContent = selected ? emojis[selected.value] : "🍽️";
      previewClient.textContent = client.value.trim() || "A nombre de...";
      previewQuantity.textContent = `${count} ${count === 1 ? "unidad" : "unidades"}`;
      previewDelivery.textContent = delivery.value || "Por definir";
    };

    form.querySelectorAll('input[name="producto"]').forEach(input =>
      input.addEventListener("change", updatePreview)
    );
    amount.addEventListener("change", updatePreview);
    client.addEventListener("input", updatePreview);
    delivery.addEventListener("change", updatePreview);
    form.querySelector('[name="telefono"]').addEventListener("input", event => {
      event.currentTarget.value = event.currentTarget.value.replace(/\D/g, "").slice(0, 10);
    });
    form.addEventListener("submit", () => {
      const button = form.querySelector(".submit-button");
      button.classList.add("is-loading");
      button.querySelector("span").textContent = "Registrando pedido...";
    });
    updatePreview();
  }

  document.querySelectorAll(".status-select").forEach(select => {
    const updateStatusColor = () => {
      select.classList.remove("status-pendiente", "status-preparando", "status-entregado", "status-cancelado");
      select.classList.add(`status-${select.value.toLowerCase()}`);
    };
    select.addEventListener("change", updateStatusColor);
  });

  document.querySelectorAll("form[data-confirm]").forEach(form => {
    form.addEventListener("submit", event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll(".toast").forEach(toast => {
    const dismiss = () => toast.remove();
    toast.querySelector(".toast-close").addEventListener("click", dismiss);
    window.setTimeout(dismiss, 6000);
  });
});
