package rlbotexample.input.dynamic_data;


/**
 * Basic information about the car.
 *
 * This class is here for your convenience, it is NOT part of the framework. You can change it as much
 * as you want, or delete it.
 */
public class ExtendedCarData extends CarData {

    /** The orientation of the car */
    public final CarOrientation orientation;

    /** True if the car is driving on the ground, the wall, etc. In other words, true if you can steer. */
    public final boolean hasWheelContact;

    /**
     * True if the car is showing the supersonic and can demolish enemies on contact.
     * This is a close approximation for whether the car is at max speed.
     */
    public final boolean isSupersonic;

    /**
     * 0 for blue team, 1 for orange team.
     */
    public final int team;

    public final int playerIndex;

    public ExtendedCarData(rlbot.flat.PlayerInfo playerInfo, int playerIndex, float elapsedSeconds) {
        super(playerInfo, elapsedSeconds);
        this.orientation = CarOrientation.fromFlatbuffer(playerInfo);
        this.isSupersonic = playerInfo.isSupersonic();
        this.team = playerInfo.team();
        this.hasWheelContact = playerInfo.hasWheelContact();
        this.playerIndex = playerIndex;
    }
}
