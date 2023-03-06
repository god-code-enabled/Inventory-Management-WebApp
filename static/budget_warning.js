function showBudgetWarning(xValue, yValue, budget) {
  if (yValue >= budget * 0.8 && yValue < budget) {
    // Display a warning if spending is between 80% and 100% of the budget
    alert("Warning: Your spending is approaching your budget limit.");
  } else if (yValue >= budget) {
    // Display an error if spending exceeds the budget
    alert("Error: Your spending has exceeded your budget limit!");
  }
}

var budgetRequest = new XMLHttpRequest();
budgetRequest.open('GET', '/static/budget.json', true);
budgetRequest.onload = function() {
  if (budgetRequest.status >= 200 && budgetRequest.status < 400) {
    // Parse the JSON response
    var budgetJSON = JSON.parse(budgetRequest.responseText);

    // Get the budget value from the JSON response
    var budget = budgetJSON.budget;

    // Make a GET request for the data JSON file
    var dataRequest = new XMLHttpRequest();
    dataRequest.open('GET', '/static/data.json', true);
    dataRequest.onload = function() {
      if (dataRequest.status >= 200 && dataRequest.status < 400) {
        // Parse the JSON response
        var dataJSON = JSON.parse(dataRequest.responseText);

        // Get the grand total value from the JSON response
        var grand_total = dataJSON.grand_total;

        // Set up the Plotly graph
        var graphDiv = document.getElementById('live-graph');
        var graphData = localStorage.getItem('graphData');

        // Check if there is saved graph data
        if (graphData) {
            // Load the saved data
            graphData = JSON.parse(graphData);
        } else {
            // Load the data from the server if there is no saved data
            graphData = JSON.parse('{{ graphJSON|safe }}');
        }

    // Add drag and hover zoom to layout
    graphData.layout.dragmode = 'pan';
    graphData.layout.hovermode = 'closest';
    graphData.layout.xaxis = {
        rangeselector: {
            buttons: [
                {
                    count: 1,
                    label: '1m',
                    step: 'month',
                    stepmode: 'backward'
                },
                {
                    count: 6,
                    label: '6m',
                    step: 'month',
                    stepmode: 'backward'
                },
                {
                    count: 1,
                    label: 'YTD',
                    step: 'year',
                    stepmode: 'todate'
                },
                {
                    count: 1,
                    label: '1y',
                    step: 'year',
                    stepmode: 'backward'
                },
                {
                    label: 'All',
                    step: 'all'
                }
            ]
        },
        rangeslider: {}
    };

    // Add the budget cap line to the layout
    graphData.layout.shapes = [
        {
            type: 'line',
            xref: 'paper',
            x0: 0,
            y0: budget,
            x1: 1,
            y1: budget,
            line:{
                color: 'red',
                width: 2,
                dash: 'dash'
            }
        }
    ];

    Plotly.plot(graphDiv, graphData.data, graphData.layout);

    var interval = setInterval(function () {
        Plotly.extendTraces(graphDiv, {
            x: [[new Date().toISOString()]],
            y: [[{{ grand_total|safe }}]],
            text: [[{{ item_details|safe }}]]
        }, [0]);

        // Save the updated graph data to local storage
        var updatedData = {
            data: graphDiv.data,
            layout: graphDiv.layout
        };
        localStorage.setItem('graphData', JSON.stringify(updatedData));

        // Check if the budget warning needs to be displayed
      showBudgetWarning(new Date().toISOString(), {{ grand_total|safe }}, budget);
