# Simulation design

## Firing order

## Data streams

A `Meter` is a place, transition or token observer feeding one or more `DataStream`s 
with observations characteristic of the `Meter`. 
Every `DataStream` has a name identifying its content and the structure of the streamed observations.

Data streams can be subscribed to. Subscriptions are a mechanism to tailor the data streams to
the interest of the analyst; it is not pub-sub! The subscription may contain a filtering condition, 
e.g. to get data only for certain places, transitions or token types.
 Only the subscribed to `DataStream`s are actually fed and only with data matching the filter.

Examples of `DataStream`s:

| Meter | Stream |Observed entity| Filtering by | Represents ... | Generated | 
|-------|--------|---------------|--------------|----------------|-----------|
| `SojournTime` | `token_visits` | token | token type, place|... the visit of a token at a given place | When the visit is completed
| `TokenCounter` | `place_population` | place| place | ... a period of stable token population at a given place | When the number of tokens changes at a place
| `TransitionInterval`|`transition_firing`|transition|transition| ... the firing of a transition | When the firing is completed

| Stream | Field name | Data type | Description
| ------|------------|-----------|--------- 
|`token_visits`|`token_id`| `long`| A unique number identifying the token
|              |`token_type`| `int`| The index of the token type.
|              |`start_time`| `double`| The time the token arrived at the place.
|              |`num_tranistions`|`long`  | The number of transitions the tokens suffered before arriving at the place.
|              |`place` |`int`        | The index of the place in the places array. 
|              |`duration` | `double` | How long the token stayed at the place (sojourn time)
|`place_population`|`start_time` | `double` | The time the stable period started
| | `place` | `int`| The index of the place with the stable period
| | `count` | `long` | The number of the tokens at the place during the stable period
| | `duration` | `double` | The duration of the stable period.
|`transition_firing`| `firing_time` | `double` | When transition was fired
| | `interval` | `double` | The time elapsed since the previous firing of the transition
| | `transition` |`int` | The index of the transition fired