# General Deliverables:

# Working Sensor

Needs to be able to send realtime data to the running application - preferably wireless.

→ If possible make it seem like we used the Helium network (need to figure out the best way to do so)

# An App

Where people can participate in a “Tree-partnership”. When they get into a tree partnership, they become responsible for the watering of this tree.

### The pages:

1. A map where they can see the state of all the trees they are in a partnership with **(Homepage)**
    
    ![IMG_0103.jpeg](attachment:e4924b2c-9f6d-446d-a89c-28832fd7776e:IMG_0103.jpeg)
    
2. Detail page per tree where you can see a virtual avatar of the tree they got into a partnership which grows when you keep the tree-soil in the right humidity range and turns yellow, losses leaves etc. or turns brown if you forget about the watering
    
    ![IMG_0105.jpeg](attachment:5c47a2f9-64cc-4e39-a56b-2b11a9764c66:IMG_0105.jpeg)
    
3. A tree picking Screen where people can look at available trees to still get in a partnership with - (maybe optional because it currently is not part of our presentation)  
    → this would be still kind of important because it might be an obvious follow up question from the jury where people can find new trees
    
    ![IMG_0107.jpeg](attachment:4686d690-2f58-40ae-9c12-8935b0637aff:IMG_0107.jpeg)
    

### Additional features of the app:

- **You have a score that grows (Duolingo style) if you are able to keep your tree’s soil humidity in a healthy range**
- **The tree is displayed according to their state**
- **You can (if you are not able to care for your tree f.e. because you are on vacation)**
- **You can name tree (tree should have a default name)**
- You can select a toggle to be notified about trees that “are in the need for help” and you can water them and get even more points based on this (directly connects to the points above - not part of our presentation at the moment thought)

---

(optional)

- **You can invite friends to allow them to join a partnership with a tree**
- Add push notification if humidity of your sensor changed but it didn’t rain (→ most likely owner took care of it)
- A form for informing that sensor doesn’t work properly (complaint)

### Data needed (high level)

- User activity data (f.e. which times of the year are people usually not able to water their plants because they are on vacation, <add more here>)
- User data (Useracc with necessary personal data + score , trees owned)
- Tree data (best case this data comes from a provider that also offers us the map so we do not need to worry about matching the coordinates on the map and is then enr
- Weather Data vs Sensor Data

# A Website:

That provides a more analytical overview of all the sensor data + a prediction for future watering bottleneck based on 1. weather predictions / historical weather data for this timespan 2. historical sensor data 3. user activity (the people that proactively added their absence in the app)

Single Page

- Map with different
- Search on top (enter address, postal code or name of tree)
- Fi button to the right of the Search Bar.

## Main views

- Maintenances (see working/inactive/defect sensors)
- Tree Map showing trees (Search bar on top to search for location or tree name)
- Click on tree shows opening panel tree details on the right (same as app)
- Filter on (working status / health)
- Show overall score (how healthy are trees in terms of watering)
- Show weather forecast (public api)

## Presentation

1. Get a funny notification about a dry tree
2. Open the app and see the tree avatar with status
3. Actually water it with the sensor inside the plant
4. Switch to the app again and see the tree recovers
5. I need to go to a vacation next week, let’s make sure I’m not gonna lose my streak and request someone to take care of it
6. The government opens the page and sees the report → clicks on filter and gets all the trees that need watering → allocates resources
7. What if the government wants to allocate resources efficiently? → We can predict the trees which will need watering based on all the data that we collect
8. Notification to another person → I need to water