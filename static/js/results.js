// DOM refs
var c = 0;

function getResult(cb) {
  $.ajax({
    type: 'GET', 
    url: '/check-task-status/',
    success: function(res) {
      c++;
      if (cb(res) == 'incomplete') {
        if (c < 50) {
          console.log('trying...')
          setTimeout(getResult(checkResponseStatus), 500)
        }
      }
    },
    error: function(res) {
      console.log('request failed')
    }
  });
};

function checkResponseStatus(res) {
    console.log(res)
    if (res.status == 'PENDING') {
      return 'incomplete';
    }
    else if (res.status === 'SUCCESS') {
      if (res.result.error) {
        $('#current-state').html('<span class="label label-danger">FAILURE</span>');
        $('#error').html(`
          <div class="bg-danger sql-error">
            <p>There was an error uploading to the database: </p>
            <p>
              ${res.result.errorMessage}
            </p>
          </div>`)
        return
      }

      $('#progress-bar').css('width', '100%');
      $('#current-state').html('<span class="label label-success">SUCCESS</span>');
      generateTable(res.result);
      return;
    }
    else if (res.status === 'PROGRESS') {
      $('#progress-bar').css('width', (100 * res.result.current / res.result.total) + '%')
      return 'incomplete'
    }
    else {
      $('#current-state').html('<span class="label label-danger">FAILURE</span>');
      $('#details').html(res.result)
      return;
    }
}

function generateTable(res) {
  var rowData = res.data.slice(1)
  var headerData = res.data[0]

  var headers = headerData.map(function(header, i) {
      return `<th>${header}</th>`
  });

  var rows = rowData.map(function(row, i) {
    var cells = row.map(function(cell) {
        return `<td>${cell}</td>`
    });

    return `<tr>${cells.join('')}</tr>`
  });

  var markup = `
    <table class="table table-striped">
      <thead>
        <tr>${headers.join('')}</tr>
      </thead>
      <tbody>
        ${rows.join('')}
      </tbody>
    </table>
  `;

  $('#details').html(markup)
}

getResult(checkResponseStatus);
