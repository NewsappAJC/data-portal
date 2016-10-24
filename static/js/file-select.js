window.onload = function() {
  $('#id_db_select, #id_db_input').each(function() {
    $(this).on('keyup change', function() {
      // Check if the input has a value
      if (!!$(this).val()) {
        if ($(this).attr('id') == 'id_db_input') {
          $('#id_db_select').prop('disabled', true)
        }
        else {
          $('#id_db_input').prop('disabled', true)
        }
      }
      else {
        if ($(this).attr('id') == 'id_db_input') {
          $('#id_db_select').prop('disabled', false)
        }
        else {
          $('#id_db_input').prop('disabled', false)
        }
      }
    })
  });
}



