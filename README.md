# Crossy-Road-1Hour-Challenge
Create Crossy Road from scratch in 1 hour, leveraging AI tools

I started off by giving Claude a detailed prompt to create the game. My plan was to have Claude make the game and then debug it along the way, which proved to be a mistake. 
I switched to copilot to try to debug the collision logic in the game, but it honestly did not work very well. I think the main problem was that I didn't give Claude enough
resources about the Pygame library, as it made some calculations wrong just due to the fact that it didn't know things like the top-left of the canvas was (0,0). So I had to go in 
and manually fix some of the collision logic, but I couldn't fix all of them in the allotted time. 
