# La Lligueta Judges

In the Catalan drone racing league [La Lligueta](https://lalligueta.com/) we have judges for every heat. What that means is that a second pilot is spectating to make sure that all the obstacles are completed sucesfuly. This assignation depends on the video system as we support multiple of them, it's for this that we have created this plugin.

## Features
- Define the video system of each pilot when creating the pilots
- Visualize the channel (more on that [here](doc/Channels%20Adjusted.md)), pilot, judge and video system in the Format tab

## Judges Algorithm
Assign a judge to every pilot on every heat with the following algorithm:
- From all the pilots in the database remove those that participate in the heat (pilots and other judges)
- Try to assign a judge with the same video system to all the heat
- If there are no pilots remaining show DVR
- If there are pilots remaining randomly select a pilot to spectate in 3d person, if we run out of pilots show DVR

## Examples
First define the video system under Format -> Pilot

![Pilot definition](doc/img/Pilots%20definition.png)

Then define your class and it's heats normaly.

![Class definition](doc/img/Class%20and%20heats.png)


Finaly, go to Format -> Judges and you will see the assignation of the judges.

> [!TIP]
>Go to the [channels adjusted](doc/Channels%20Adjusted.md) document to understand what the options are in the *Channel* column


![Judges assignation](doc/img/Judges.png)