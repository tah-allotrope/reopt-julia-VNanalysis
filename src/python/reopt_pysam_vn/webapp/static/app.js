document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("new-deal-form");
  if (!form) return;
  var errorEl = document.getElementById("form-error");

  form.addEventListener("submit", function (evt) {
    evt.preventDefault();
    errorEl.textContent = "";
    var data = new FormData(form);
    fetch("/api/deals", { method: "POST", body: data })
      .then(function (resp) {
        if (resp.status === 202) {
          return resp.json().then(function (body) {
            window.location.href = "/runs/" + body.run_id;
          });
        }
        return resp.json().then(function (body) {
          throw new Error(body.detail || "submission failed");
        });
      })
      .catch(function (err) {
        errorEl.textContent = err.message;
      });
  });
});
