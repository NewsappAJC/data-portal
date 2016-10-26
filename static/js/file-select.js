window.onload = function() {
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



