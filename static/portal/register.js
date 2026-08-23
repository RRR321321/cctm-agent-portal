// 注册页用户名校验：空格/非法字符 -> 红色警告，禁止提交
(function () {
  var input = document.getElementById("reg-username");
  var warn = document.getElementById("name-warn");
  var submit = document.getElementById("reg-submit");
  var form = document.getElementById("regform");
  if (!input) return;

  function check() {
    var v = input.value;
    var msg = "";
    if (/\s/.test(v)) {
      msg = "用户名不能有空格";
    } else if (v && !/^[a-z][a-z0-9_-]*$/.test(v.toLowerCase())) {
      msg = "只能用小写字母、数字、下划线和连字符，且以字母开头（请用名字拼音）";
    } else if (v !== v.toLowerCase()) {
      msg = "请使用小写字母（名字拼音）";
    }
    if (msg) {
      warn.textContent = msg;
      warn.style.display = "block";
      submit.disabled = true;
    } else {
      warn.style.display = "none";
      submit.disabled = false;
    }
    return !msg;
  }

  input.addEventListener("input", check);
  form.addEventListener("submit", function (e) {
    if (!check()) {
      e.preventDefault();
    } else {
      input.value = input.value.toLowerCase().trim();
    }
  });
})();
