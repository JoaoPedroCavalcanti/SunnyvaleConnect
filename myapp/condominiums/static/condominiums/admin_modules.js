(function ($) {
  "use strict";

  function bindModuleToggles() {
    var $all = $("#id_enable_all_modules");
    var $boxes = $("#id_enabled_modules input[type=checkbox]");
    if (!$all.length || !$boxes.length) {
      return;
    }

    function syncAllFromBoxes() {
      var total = $boxes.length;
      var checked = $boxes.filter(":checked").length;
      $all.prop("checked", total > 0 && checked === total);
    }

    $all.off("change.condoModules").on("change.condoModules", function () {
      $boxes.prop("checked", $all.is(":checked"));
    });

    $boxes.off("change.condoModules").on("change.condoModules", syncAllFromBoxes);
    syncAllFromBoxes();
  }

  $(bindModuleToggles);
  $(document).on("formset:added", bindModuleToggles);
})(django.jQuery);
