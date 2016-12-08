// Globals
var csrf,
    $btn;

// Event handler for submit button
$('#file-submit').on('click', function() {
  // Get the date from the form and send it as an AJAX post request
  var data = new FormData($('#upload-form')[0]);
  csrf = data.get('csrfmiddlewaretoken');
  postForm(data);

  // Defined as a global so that we can enable/disable from within multiple
  // functions
  $btn = $(this).button('loading');
});


function postForm(data) {
  $.ajax({
    url: '/',
    type: 'POST', 
    contentType: false,
    processData: false,
    cache: false,
    // We have to add a CSRF token as a header or Django will complain
    headers: {'X-CSRFToken': csrf},
    data: data,
    success: function(res) {
      // Redirect to the categorize page if form validates and upload to S3
      // succeeds
      window.location.href = '/categorize/';
    },
    error: function(res) {
      addErrorMessages(JSON.parse(res.responseJSON));
      $btn.button('reset');
    }
  });
};


function addErrorMessages(errors) {
  // Clear existing errors
  $('.errors').each(function() {
    $(this).html('');
  });

  // Loop through errors
  $.each(errors, function(err) {
    messages = errors[err]
    // We're only interested in the messages for each error
    fmessages = messages.map(function(m) {
      return m.message;
    });

    // Some errors aren't linked to any particular field
    if  (err === '__all__') {
      $('#non-field-errors').text(fmessages.join(', '));
    }
    else {
      // Append error messages specified for different field
      var field = $('#id_' + err);
      errorDiv = field.siblings()[1];
      $(errorDiv).text(fmessages.join(', ')); // Use text instead of HTML to prevent XSS
    };
  });
};
