window.onload = function() {
  // If data is selected or entered in the DB select boxes, the other
  // DB input field should be temporarily disabled. If the field is cleared,
  // the other DB input can be re-enabled
  function checkAndDisable(input) {
    if (!!$(input).val()) {
      if ($(input).attr('id') == 'id_db_input') {
        $('#id_db_select').prop('disabled', true)
      }
      else {
        $('#id_db_input').prop('disabled', true)
      }
    }
    else {
      if ($(input).attr('id') == 'id_db_input') {
        $('#id_db_select').prop('disabled', false)
      }
      else {
        $('#id_db_input').prop('disabled', false)
      }
    }
  };

  $('#id_db_select, #id_db_input').each(function() {
    checkAndDisable(this);
    $(this).on('keyup change', function() {
      checkAndDisable(this)
    })
  });
}



