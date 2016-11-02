var csrf;

// Get data from form
$('#file-submit').on('click', function() {
  $('#progress-holder').show();
  var data = new FormData($('#upload-form')[0]);

  csrf = data.get('csrfmiddlewaretoken');

  postForm(data);
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
      getResult(checkResponseStatus);
    },
    error: function(res) {
      console.log('request failed')
    }
  });
};

function getResult(cb) {
  $.ajax({
    type: 'GET', 
    url: '/check-task-status/',
    success: function(res) {
      if (cb(res) == 'incomplete') {
        console.log('trying...')
        setTimeout(getResult(checkResponseStatus), 500)
      }
    },
    error: function(res) {
      console.log('request failed')
    }
  });
};


function checkResponseStatus(res) {
    console.log(res)
    if (res.status == 'PROGRESS') {
      $('#progress-bar').css('width', (100 * res.result.current / res.result.total) + '%')
      $('#progress-message').html(res.result.message)
      return 'incomplete'
    }
    else if (res.status === 'SUCCESS') {
      $('#progress-bar').removeClass('active')
      if (res.result.error) {
        $('#current-state').html('<span class="label label-danger">FAILURE</span>');
        $('#progress-message').html('Error')
        return
      }

      $('#progress-bar').css('width', '100%');
      $('#current-state').html('<span class="label label-success">SUCCESS</span>');
      $('#progress-message').html('Finished')
      $('#tempfile').val(res.result.s3_path) // Hold the s3 path in a hidden input so we can pass it to the next view
      window.location.href = '/categorize/';

      return;
    }
    else if (res.status == 'PENDING') {
      return 'incomplete';
    }
    else {
      $('#current-state').html('<span class="label label-danger">FAILURE</span>');
      $('#progress-bar').removeClass('active')
      $('#details').html(res.result)
      return;
    }
}

