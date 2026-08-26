/**
 * Máscara de moeda pt-BR (R$ 0,00) para inputs com [data-moeda-input].
 * Centavos são acumulados à direita (1 → R$ 0,01); não lê dígitos do texto formatado.
 * No submit, o value vira decimal com ponto (ex: 1234.56).
 */
(function (global) {
  "use strict";

  var MAX_CENTS = 999999999999; // 12 dígitos em centavos

  function onlyDigits(str) {
    return String(str || "").replace(/\D/g, "");
  }

  function formatCents(cents) {
    return (cents / 100).toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
    });
  }

  function parseDecimalToCents(decimalStr) {
    var s = String(decimalStr == null ? "" : decimalStr).trim();
    if (!s) return 0;
    var t = s.replace(/[R$\s]/gi, "");
    if (t.indexOf(",") >= 0 && t.indexOf(".") >= 0) {
      t = t.replace(/\./g, "").replace(",", ".");
    } else if (t.indexOf(",") >= 0) {
      t = t.replace(",", ".");
    }
    var num = Number.parseFloat(t);
    if (Number.isNaN(num)) return 0;
    return Math.min(Math.round(num * 100), MAX_CENTS);
  }

  function getCents(input) {
    var n = parseInt(input.dataset.moedaCents || "0", 10);
    return Number.isNaN(n) ? 0 : n;
  }

  function allowEmpty(input) {
    return input && input.dataset.moedaAllowEmpty === "1";
  }

  function setCents(input, cents) {
    cents = Math.max(0, Math.min(cents, MAX_CENTS));
    input.dataset.moedaCents = String(cents);
    if (cents === 0 && allowEmpty(input) && !input.dataset.moedaTouched) {
      input.value = "";
      return;
    }
    input.value = formatCents(cents);
  }

  function parseToDecimalString(valueOrInput) {
    if (valueOrInput && valueOrInput.dataset && valueOrInput.dataset.moedaCents != null) {
      return (getCents(valueOrInput) / 100).toFixed(2);
    }
    return (parseDecimalToCents(valueOrInput) / 100).toFixed(2);
  }

  function applySubmitValue(input) {
    if (allowEmpty(input) && getCents(input) === 0) {
      input.value = "";
      return;
    }
    input.value = parseToDecimalString(input);
  }

  function appendDigit(input, digit) {
    var cents = getCents(input);
    var next = cents * 10 + digit;
    if (next <= MAX_CENTS) setCents(input, next);
  }

  function removeLastDigit(input) {
    setCents(input, Math.floor(getCents(input) / 10));
  }

  function isCoarsePointer() {
    try {
      return window.matchMedia("(pointer: coarse)").matches;
    } catch (err) {
      return false;
    }
  }

  function collapseSelection(input) {
    if (typeof input.setSelectionRange !== "function") return;
    var len = (input.value || "").length;
    try {
      input.setSelectionRange(len, len);
    } catch (err) {
      /* ignore */
    }
  }

  function hasTextSelection(input) {
    if (
      typeof input.selectionStart !== "number" ||
      typeof input.selectionEnd !== "number"
    ) {
      return false;
    }
    return input.selectionStart !== input.selectionEnd;
  }

  function clearMoedaValue(input) {
    input.dataset.moedaCents = "0";
    if (allowEmpty(input)) {
      input.value = "";
    } else {
      input.value = formatCents(0);
    }
  }

  function handleDelete(input) {
    if (hasTextSelection(input)) {
      clearMoedaValue(input);
    } else {
      removeLastDigit(input);
    }
  }

  function insertDigit(input, digit) {
    if (hasTextSelection(input)) {
      setCents(input, digit);
    } else {
      appendDigit(input, digit);
    }
  }

  function bindMoedaEvents(input) {
    input.addEventListener("keydown", function (e) {
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      if (e.key >= "0" && e.key <= "9") {
        e.preventDefault();
        input.dataset.moedaTouched = "1";
        insertDigit(input, parseInt(e.key, 10));
        return;
      }

      if (e.key === "Backspace" || e.key === "Delete") {
        e.preventDefault();
        input.dataset.moedaTouched = "1";
        handleDelete(input);
      }
    });

    input.addEventListener("beforeinput", function (e) {
      if (e.isComposing) return;

      if (e.inputType === "insertText" && e.data && /^\d$/.test(e.data)) {
        e.preventDefault();
        input.dataset.moedaTouched = "1";
        insertDigit(input, parseInt(e.data, 10));
        return;
      }

      if (
        e.inputType === "deleteContentBackward" ||
        e.inputType === "deleteContentForward" ||
        e.inputType === "deleteContent"
      ) {
        e.preventDefault();
        input.dataset.moedaTouched = "1";
        handleDelete(input);
      }
    });

    input.addEventListener("paste", function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData("text");
      input.dataset.moedaTouched = "1";
      setCents(input, parseDecimalToCents(text));
    });

    input.addEventListener("input", function () {
      /* Reverte alteração nativa do navegador no texto formatado. */
      setCents(input, getCents(input));
    });

    input.addEventListener("focus", function () {
      input.dataset.moedaTouched = "1";
      if (!input.value && !allowEmpty(input)) {
        setCents(input, 0);
      }
      if (isCoarsePointer()) return;
      setTimeout(function () {
        try {
          input.select();
        } catch (err) {
          /* ignore */
        }
      }, 0);
    });

    input.addEventListener("blur", function () {
      if (allowEmpty(input) && getCents(input) === 0) {
        input.value = "";
        input.dataset.moedaCents = "0";
        delete input.dataset.moedaTouched;
      }
    });
  }

  function init(input) {
    if (!input || input.dataset.moedaInitialized === "1") return;
    input.dataset.moedaInitialized = "1";
    input.type = "text";
    input.setAttribute("inputmode", "numeric");
    input.setAttribute("autocomplete", "off");
    if (!input.classList.contains("input-moeda")) {
      input.classList.add("input-moeda");
    }

    var initial =
      input.dataset.initialDecimal !== undefined
        ? input.dataset.initialDecimal
        : input.value;
    if (String(initial || "").trim()) {
      setCents(input, parseDecimalToCents(initial));
    } else if (allowEmpty(input)) {
      input.value = "";
      input.dataset.moedaCents = "0";
    } else {
      setCents(input, 0);
    }

    bindMoedaEvents(input);
  }

  function initAll(root) {
    var scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll("[data-moeda-input]").forEach(init);
  }

  function setValueFromDecimal(input, decimalStr) {
    if (!input) return;
    if (input.dataset.moedaInitialized !== "1") init(input);
    if (!String(decimalStr || "").trim() && allowEmpty(input)) {
      input.value = "";
      input.dataset.moedaCents = "0";
      delete input.dataset.moedaTouched;
      return;
    }
    setCents(input, parseDecimalToCents(decimalStr || "0"));
    input.dataset.moedaTouched = "1";
  }

  function reset(input) {
    if (!input) return;
    delete input.dataset.moedaTouched;
    if (allowEmpty(input)) {
      input.value = "";
      input.dataset.moedaCents = "0";
    } else {
      setCents(input, 0);
    }
  }

  document.addEventListener(
    "submit",
    function (e) {
      var form = e.target;
      if (!form || !form.querySelectorAll) return;
      form.querySelectorAll("[data-moeda-input]").forEach(applySubmitValue);
    },
    true
  );

  document.addEventListener("reset", function (e) {
    var form = e.target;
    if (!form || !form.querySelectorAll) return;
    form.querySelectorAll("[data-moeda-input]").forEach(reset);
  });

  function onReady() {
    initAll(document);
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState !== "visible") return;
    document.querySelectorAll("[data-moeda-input]").forEach(function (input) {
      if (document.activeElement === input) collapseSelection(input);
    });
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }

  global.MoedaInput = {
    init: init,
    initAll: initAll,
    parseToDecimalString: parseToDecimalString,
    setValueFromDecimal: setValueFromDecimal,
    applySubmitValue: applySubmitValue,
    reset: reset,
  };
})(window);
