library(shiny)
library(leaflet)
library(DT)




# UI
###############################################################
ui <- fluidPage(
  
  titlePanel("Location Viewer"),
  sidebarLayout(
    sidebarPanel(
      numericInput("lat", "Latitude:", value = 25.286, step = 0.01),
      numericInput("lng", "Longitude:", value = -81.178, step = 0.01),
      actionButton("go", "Show on Map", class = "btn-primary")
    ),
    mainPanel(
      
      leafletOutput("map", height = "500px"),
      hr(),
      h4("Saved Locations"),
      DTOutput("table")
    )
  )
)

################################################################










# Server
###############################################################

server <- function(input, output, session) {
  locations <- reactiveVal(data.frame(
    ID = integer(),
    Latitude = numeric(),
    Longitude = numeric(),
    stringsAsFactors = FALSE
  ))
  
  output$map <- renderLeaflet({
    
    leaflet() %>%
      addProviderTiles(providers$Esri.WorldImagery) %>%
      addProviderTiles(providers$CartoDB.PositronOnlyLabels) %>%
      setView(lng = -81.178, lat = 25.286, zoom = 13)
    
  })
  
  observeEvent(input$go, {
    new_row <- data.frame(
      ID = nrow(locations()) + 1,
      
      Latitude = input$lat,
      Longitude = input$lng,
      
      stringsAsFactors = FALSE
      
      
    )
    locations(rbind(locations(), new_row))
    
    leafletProxy("map") %>%
      clearMarkers() %>%
      setView(lng = input$lng, lat = input$lat, zoom = 15) %>%
      
      addCircleMarkers(
        
        data = locations(),
        lng = ~Longitude, lat = ~Latitude,
        radius = 8, color = "#ff3333", fillColor = "#ff3333",
        fillOpacity = 0.9, weight = 2, opacity = 1,
        popup = ~paste("ID:", ID, "<br>Lat:", Latitude, "<br>Lng:", Longitude)
      )
  })
  
  output$table <- renderDT({
    datatable(locations(), options = list(pageLength = 10, dom = "tip"), rownames = FALSE)
  })
}

#################################################################







shinyApp(ui, server)




















