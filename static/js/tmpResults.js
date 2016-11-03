var csrf,
    $btn;

// Get data from form
$('#file-submit').on('click', function() {
  // Get the date from the form and send AJAX post request
  var data = new FormData($('#upload-form')[0]);
  csrf = data.get('csrfmiddlewaretoken');
  postForm(data);

  $btn = $(this).button('loading');
});

function postForm(data) {
  $.ajax({
    url: '/',
    type: 'POST', 
    contentType: false,
    processData: false,
    cache: false,
    headers: {'X-CSRFToken': csrf},
    data: data,
    success: function(res) {
      window.location.href = '/categorize/';
    },
    error: function(res) {
      addErrorMessages(JSON.parse(res.responseJSON));
      $btn.button('reset');
    }
  });
};

function addErrorMessages(errors) {
  $('.errors').each(function() {
    $(this).html('');
  });

  $.each(errors, function(err) {
    // Loop through messages and create a list
    messages = errors[err]
    fmessages = messages.map(function(m) {
      return m.message;
    });

    if  (err === '__all__') {
      $('#non-field-errors').text(fmessages.join(', '));
    }
    else {
      // Append error messages for each field
      var field = $('#id_' + err);
      errorDiv = field.siblings()[1];
      $(errorDiv).text(fmessages.join(', ')); // Use text instead of HTML to prevent XSS
    };
  });
};
