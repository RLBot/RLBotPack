import math

def ball_path_predict(data_loc_speed): # [self.game_time, self.ball_lt_z, self.ball_lt_speed_z]
    start_on=0
    #print(data_loc_speed)
    loc_x=data_loc_speed[1][0][start_on]
    loc_y=data_loc_speed[1][1][start_on]
    loc_z=data_loc_speed[1][2][start_on]
    speed_x=data_loc_speed[2][0][start_on]
    speed_y=data_loc_speed[2][1][start_on]
    speed_z=data_loc_speed[2][2][start_on]
    ang_speed_x=data_loc_speed[3][0][start_on]
    ang_speed_y=data_loc_speed[3][1][start_on]
    ang_speed_z=data_loc_speed[3][2][start_on]
    time_i=data_loc_speed[0][start_on]
    timer=0
    time_l=[]
    ground_t=[]
    predic_loc_z_t=[]
    predic_loc_x_t=[]
    predic_loc_y_t=[]
    ground_loc_x=[]
    ground_loc_y=[]
    ground_loc_z=[]
    predicted_loc=[[],[[],[],[]],[],[[],[],[]],[],[[],[],[]]]
    bounce_t=0
    goal=False
    ground_next=False
    ball_rolling=False
    air_friction=0.013
    gravity=-650
    ball_radius=93
    step=1/120
    perpendicular_restitution=0.60
    #todo: change depending on entry angle
    paralel_restitution=0.713
    spin_inertia=0.4
    while timer < 5:
        time=timer-bounce_t
        #z
        loc_z_t=loc_z+((speed_z*(1-air_friction*time))*time)+(0.5*(gravity)*(time**2))
        #x
        loc_x_t=loc_x+((speed_x*(1-air_friction*time))*time)
        #y
        loc_y_t=loc_y+((speed_y*(1-air_friction*time))*time)

        if loc_z_t<ball_radius:
            speed_z=(speed_z*(1-air_friction*time-step)+gravity*(time-step))
            speed_z=abs(speed_z)*perpendicular_restitution
            loc_z=ball_radius
            loc_x=loc_x+((speed_x*(1-air_friction*time))*time)
            loc_y=loc_y+((speed_y*(1-air_friction*time))*time)
            bounce_t=timer
            ground_next=True
            if speed_z < 0.01:
                speed_z=0
                ground_next=False
                ball_rolling=True
            speed_x=speed_x*(1-air_friction*time)#*paralel_restitution
            speed_y=speed_y*(1-air_friction*time)#*paralel_restitution

            if True:
                entry_angle = abs(math.atan2(speed_z,math.sqrt(speed_x**2+speed_y**2)))/math.pi*180
                # some more magic numbers
                custom_friction = (paralel_restitution-1)/(28)*entry_angle +1

                # limiting custom_friction to range [e1, 1]
                if custom_friction<paralel_restitution: custom_friction=paralel_restitution

                speed_x = (speed_x + ang_speed_y * ball_radius * spin_inertia) * paralel_restitution
                speed_y = (speed_y - ang_speed_x * ball_radius * spin_inertia) * paralel_restitution

                ang_speed_x = -speed_y/ball_radius
                ang_speed_y = speed_x/ball_radius
                ang_speed_z = speed_z/ball_radius

                # limiting ball spin
                total_ang_speed = math.sqrt(ang_speed_x**2+ang_speed_y**2+ang_speed_z**2)
                if total_ang_speed > 6:
                    ang_speed_x,ang_speed_y,ang_speed_z = 6*ang_speed_x/total_ang_speed, 6*ang_speed_y/total_ang_speed, 6*ang_speed_z/total_ang_speed
        elif abs(loc_z_t)>2044-ball_radius:
            loc_z=2044-ball_radius
            speed_z=-(speed_z*(1-air_friction*time-step)+gravity*(time-step))
            #speed_z=speed_z*(1-air_friction*(time))
            speed_z=speed_z*perpendicular_restitution

            loc_y=loc_y+((speed_y*(1-air_friction*(time)))*(time))
            speed_y=speed_y*(1-air_friction*(time)) #*paralel_restitution

            loc_x=loc_x+((speed_x*(1-air_friction*(time)))*(time))
            speed_x=speed_x*(1-air_friction*(time)) #*paralel_restitution

            if True:

                entry_angle = abs(math.atan2(speed_z,math.sqrt(speed_x**2+speed_y**2)))/math.pi*180
                # some more magic numbers
                custom_friction = (paralel_restitution-1)/(28)*entry_angle +1

                # limiting custom_friction to range [e1, 1]
                if custom_friction<paralel_restitution: custom_friction=paralel_restitution

                speed_x = (speed_x + ang_speed_z * ball_radius * spin_inertia) * custom_friction
                speed_y = (speed_y + ang_speed_z * ball_radius * spin_inertia) * paralel_restitution
                #speed_z = (speed_x - ang_speed_y * ball_radius * spin_inertia) * paralel_restitution


                ang_speed_x = speed_z/ball_radius
                ang_speed_y = speed_z/ball_radius
                #ang_speed_z = speed_y/ball_radius

                # limiting ball spin
                total_ang_speed = math.sqrt(ang_speed_x**2+ang_speed_y**2+ang_speed_z**2)
                if total_ang_speed > 6:
                    ang_speed_x,ang_speed_y,ang_speed_z = 6*ang_speed_x/total_ang_speed, 6*ang_speed_y/total_ang_speed, 6*ang_speed_z/total_ang_speed

            bounce_t=timer
        elif abs(loc_x_t)>4096-ball_radius:
            if loc_x>0:
                loc_x=4096-ball_radius
            else:
                loc_x=-4096+ball_radius

            speed_x=speed_x*(1-air_friction*(time))
            speed_x=-speed_x*perpendicular_restitution

            loc_y=loc_y+((speed_y*(1-air_friction*(time)))*(time))
            speed_y=speed_y*(1-air_friction*(time))#*paralel_restitution

            loc_z=loc_z+((speed_z*(1-air_friction*(time)))*(time))+(0.5*(gravity)*((time)**2))
            speed_z=(speed_z*(1-air_friction*(time-step))+gravity*((time-step)))#*paralel_restitution #implement spin

            if True:

                entry_angle = abs(math.atan2(speed_z,math.sqrt(speed_x**2+speed_y**2)))/math.pi*180
                # some more magic numbers
                custom_friction = (paralel_restitution-1)/(28)*entry_angle +1

                # limiting custom_friction to range [e1, 1]
                if custom_friction<paralel_restitution: custom_friction=paralel_restitution
                #speed_x = (speed_x + ang_speed_z * ball_radius * spin_inertia) * custom_friction
                speed_y = (speed_y + ang_speed_z * ball_radius * spin_inertia) * paralel_restitution
                speed_z = (speed_z - ang_speed_y * ball_radius * spin_inertia) * paralel_restitution


                #ang_speed_x = -speed_z/ball_radius
                ang_speed_y = -speed_z/ball_radius
                ang_speed_z = speed_y/ball_radius

                # limiting ball spin
                total_ang_speed = math.sqrt(ang_speed_x**2+ang_speed_y**2+ang_speed_z**2)
                if total_ang_speed > 6:
                    ang_speed_x,ang_speed_y,ang_speed_z = 6*ang_speed_x/total_ang_speed, 6*ang_speed_y/total_ang_speed, 6*ang_speed_z/total_ang_speed

            bounce_t=timer
        elif abs(loc_y_t)>5120-ball_radius:
            if abs(loc_x_t)<892.755-ball_radius and abs(loc_z_t)<642.775-ball_radius:
                goal=True
                break
            if loc_y>0:
                loc_y=5120-ball_radius
            else:
                loc_y=-5120+ball_radius

            speed_y=speed_y*(1-air_friction*time)#*paralel_restitution
            speed_y=-speed_y*perpendicular_restitution

            loc_z=loc_z+((speed_z*(1-air_friction*time))*time)+(0.5*(gravity)*(time**2))
            loc_x=loc_x+((speed_x*(1-air_friction*time))*time)

            speed_x=speed_x*(1-air_friction*time)#*paralel_restitution
            speed_z=(speed_z*(1-air_friction*(time-step))+gravity*((time-step)))#*paralel_restitution

            if True:

                entry_angle = abs(math.atan2(speed_z,math.sqrt(speed_x**2+speed_y**2)))/math.pi*180
                # some more magic numbers
                custom_friction = (paralel_restitution-1)/(28)*entry_angle +1

                # limiting custom_friction to range [e1, 1]
                if custom_friction<paralel_restitution: custom_friction=paralel_restitution
                speed_x = (speed_x - ang_speed_z * ball_radius * spin_inertia) * paralel_restitution
                #speed_y = (speed_y + ang_speed_z * ball_radius * spin_inertia) * custom_friction
                speed_z = (speed_z + ang_speed_x * ball_radius * spin_inertia) * custom_friction


                ang_speed_x = -speed_z/ball_radius
                #ang_speed_y = -speed_z/ball_radius
                ang_speed_z = speed_y/ball_radius

                # limiting ball spin
                total_ang_speed = math.sqrt(ang_speed_x**2+ang_speed_y**2+ang_speed_z**2)
                if total_ang_speed > 6:
                    ang_speed_x,ang_speed_y,ang_speed_z = 6*ang_speed_x/total_ang_speed, 6*ang_speed_y/total_ang_speed, 6*ang_speed_z/total_ang_speed

            bounce_t=timer
        else:
            predic_loc_z_t+=[loc_z_t]
            predic_loc_x_t+=[loc_x_t]
            predic_loc_y_t+=[loc_y_t]
            tick_time=[timer+time_i]
            time_l+=tick_time
            timer+=step
            if ground_next:
                ground_t+=tick_time
                ground_loc_x+=[loc_x_t]
                ground_loc_y+=[loc_y_t]
                ground_loc_z+=[loc_z_t]
                ground_next=False
            if ball_rolling:
                ground_loc_x+=[loc_x_t]
                ground_loc_y+=[loc_y_t]
                ground_loc_z+=[loc_z_t]
    predicted_loc[0]=time_l
    predicted_loc[1][0]=predic_loc_x_t
    predicted_loc[1][1]=predic_loc_y_t
    predicted_loc[1][2]=predic_loc_z_t
    predicted_loc[2]=ground_t
    predicted_loc[3][0]=ground_loc_x
    predicted_loc[3][1]=ground_loc_y
    predicted_loc[3][2]=ground_loc_z
    if goal:
        predicted_loc[4]=timer
        predicted_loc[5][0]=loc_x
        predicted_loc[5][1]=loc_y
        predicted_loc[5][2]=loc_z
    else:
        predicted_loc[4]=0
        predicted_loc[5][0]=0
        predicted_loc[5][1]=0
        predicted_loc[5][2]=0
    return predicted_loc
