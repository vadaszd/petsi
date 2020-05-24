# Simulation design

## Firing order

## Data streams

A `Meter` is a `Plugin` feeding one or more `DataStream`s with records characteristic of the `Meter`. 
Every `DataStream` has a name identifying its content and the structure of the streamed records.

Data streams can be subscribed to. Subscriptions are a mechanism to tailor the data streams to
the interest of the analyst; it is not pub-sub! The subscription may contain a filtering condition, 
e.g. to get data only for certain places, transitions or token types.
 Only the subscribed to `DataStream`s are actually fed and only with data matching the filter.

Examples of `DataStream`s:

| Meter | Stream  | Filtering by | Represents ... | Generated | 
|-------|--------------|-----------|-----|-----------|
| `SojournTime` | `token.visit` | place|... the visit of a token at a given place | When a visit is completed
|               | `token.habitancy` | place | ... all the portions of time a token spends at a place during its whole life| When the token is destroyed
|               | `token.life` | token type |... the life of a token | When the token is destroyed
| `TokenCounter` | `place.population` | place | ... a period of stable token population at a given place | When the number of tokens changes at a place
| `TransitionInterval`|`transition.firing`| transition | ... the firing of a transition | When the firing is completed

| Stream | Field name | Data type | Description
| ------|------------|-----------|--------- 
|`token.visit` | `start.time` | `double` | The time the token arrived at the place
| | `place` | `int` | The index of the place in the places array. 
| | `duration` | `double` | How long the token stayed at the place, sojourn time
|`token.habitancy` | `places` | `int[]` |  The index of the places visited by the token during its whole life
|  | `time.split` | `double[]` |  The life-time of the token split by the visited places. Each value correspond to the matching place-index in the `places` array.  
|`token.life` | `construction.time` | `double` | The time the token was created
| | `life.time` | `double` | The time elapsed between creating and destroying the token
|`place.population`|`start.time` | `double` | The time the stable period started
| | `place` | `int`| The index of the place with the stable period
| | `count` | `long` | The number of the tokens at the place during the stable period
| | `duration` | `double` | The duration of the stable period.
|`transition.firing`| `time` | `double` | When transition was fired
| | `interval` | `double` | The time elapsed since the previous firing of the transition
| | `transition` |`int` | The index of the transition fired