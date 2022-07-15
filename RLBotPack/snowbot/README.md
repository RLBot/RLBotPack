# Snowbot
A bot to draw Rocket League snow art. Runs on gcode like a CNC or 3D printer. Currently uses state-setting to travel but might be more intelligent in the future. The bot works best with images with few colors, preferably silhouettes. It is far from perfect and may decide to put a line across your image if it feels like it, but it's good enough and it will definetly get a likeness across.
## How to set up Cura
This bot uses gcode sliced by [Cura](https://ultimaker.com/software/ultimaker-cura) to run. It must be sliced using Cura so the gcode comments are predictable. Even though UE says that 1uu=10cm, this uses 1 gcode unit = 100uu so Cura can handle it. This will draw the bottom layer.
### Printer settings:
- size: X81.92mm Y102.40mm
- origin at center
- 1 extruder
- extruder nozzle size .75mm
- height doesnt matter, I used 100mm
- no heated bed
- marlin flavor
- no start gcode (z moves can throw off layer detection)
- other settings dont matter
### Profile settings:
Use the profile `snowbot_solid.curaprofile`. To import it, press Ctrl+J to manage profiles and press the import button, then select the `.curaprofile`.
## How to slice an image
1. You don't neeed to do this if you want to use one of the example gcodes. Otherwise, open Cura.
2. Hit the folder icon and open your image.
3. The height should be .4, the base 0, and width should be 80 or less and depth 100 or less. Darker should be higher with a linear color model and 1% transmittance with 1 smoothing.
4. Hit Ok to import your image.
5. Clicking on the 3 sliders icon to open the print settings.
6. If there's not a dropdown to select a profile, hit the Custom button.
7. Select Snowbot solid from the profile dropdown.
8. Press the Slice button.
9. Once slicing has completed, preview the moves if you'd like, then save the gcode to disk somewhere.
## How to draw an image gcode
1. Slice your image/model and save it to disk somewhere or use one of the image gcodes in the `examples` folder
2. With RLBot, start a game on a mannfield-snowy with only Snowbot, unlimited time, gravity at super high, and max score at one (so you can end the game and save the replay).
3. Browse with the bot's interface and press select file.
4. Wait for the bot to finish. Be aware that many things will reset the progress, including opening the game settings.
5. Take a screenshot of the art if you wish.
6. If you want to save the replay, go into the state setting sasnbox in RLBot and drag the ball into the goal. This will end the game
if you have set your mutators properly.
7. After the game ends, you can save your replay.
## Statesetting
This bot currently uses statesetting to travel and to move the ball out of the way. If I have the ~~time~~ motivation I will add inteligent movement to jump and aerial from one spot to another.