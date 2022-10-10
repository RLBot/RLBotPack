import math
from itertools import zip_longest
from typing import Tuple, List, Type, Union, Dict, Optional, Any, Iterable

import numpy as np
import torch
from numba import jit
from sklearn.preprocessing import OneHotEncoder
from torch import nn
from torch.distributions import Categorical

flip_timeout = 1.5

invert_player_data_const = np.array([-1., -1., 1., 1., 1., 1., -1., -1., 1., -1., -1., 1., 1., 1., 1., 1.], dtype=np.float32)
invert_ball_data_const = np.array([-1., -1., 1., -1., -1., 1., -1., -1., 1.], dtype=np.float32)


@jit(nopython=True, fastmath=True)
def invert_player_data(player_data: np.ndarray) -> np.ndarray:
    assert len(player_data) == 16
    player_data = player_data * invert_player_data_const
    player_data[4] = invert_yaw(player_data[4])
    return player_data


@jit(nopython=True, fastmath=True)
def invert_boost_data(boost_data: np.ndarray) -> np.ndarray:
    assert boost_data.shape[0] == 34
    # just the inverse
    return boost_data[::-1]


@jit(nopython=True, fastmath=True)
def invert_ball_data(ball_data: np.ndarray) -> np.ndarray:
    assert len(ball_data) == 9
    ball_data = ball_data * invert_ball_data_const
    return ball_data


@jit(nopython=True, fastmath=True)
def invert_yaw(yaw):
    tol = 1e-4
    assert -math.pi - tol <= yaw <= math.pi + tol
    yaw += math.pi  # yaw in [- pi, pi]
    if yaw > math.pi:
        yaw -= 2 * math.pi
    assert -math.pi - tol <= yaw <= math.pi + tol
    return yaw


enc = OneHotEncoder(sparse=False, drop='if_binary',
                    categories=[np.array([0., 1., 2.]), np.array([0., 1., 2., 3., 4.]), np.array([0., 1., 2., 3., 4.]), np.array([0., 1., 2.]), np.array([0., 1.]), np.array([0., 1.]),
                                np.array([0., 1.])])


@jit(nopython=True, fastmath=True)
def get_distance(array_0: np.ndarray, array_1: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    # assert array_0.shape[0] == 3
    # assert array_1.shape[0] == 3

    diff = array_0 - array_1

    norm = np.linalg.norm(diff)

    return diff, np.array(norm, dtype=np.float32).reshape(1)


@jit(nopython=True, fastmath=True)
def get_speed(array: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    speed = np.linalg.norm(array)

    is_super_sonic = speed >= 2200.0

    return np.array(speed, dtype=np.float32).reshape(1), np.array(is_super_sonic, dtype=np.float32).reshape(1)


@jit(nopython=True, fastmath=True)
def impute_features(player_car_state: np.ndarray, opponent_car_data: np.ndarray, pads, ball_data: np.ndarray, prev_action_enc: np.ndarray) -> np.ndarray:
    # assert x_train.shape[0] == input_features_replay

    player_0 = player_car_state
    player_1 = opponent_car_data
    boost_pads_timer = pads
    ball = ball_data

    # assert player_0.shape[0] == 16
    # assert player_1.shape[0] == 16
    # assert ball.shape[0] == 9

    player_0_pos = player_0[0:3]
    # player_0_rotation = player_0[:, 3:6]
    player_0_velocity = player_0[6:9]
    # player_0_ang_velocity = player_0[:, 9:12]
    player_0_demo_timer = player_0[12]

    player_1_pos = player_1[0:3]
    # player_1_rotation = player_1[:, 3:6]
    player_1_velocity = player_1[6:9]
    # player_1_ang_velocity = player_1[:, 9:12]
    player_1_demo_timer = player_1[12]

    ball_pos = ball[0:3]
    ball_velocity = ball[3:6]
    # ball_1_ang_velocity = ball[:, 6:9]

    is_boost_active = boost_pads_timer == 0.0
    player_0_is_alive = player_0_demo_timer == 0.0
    player_1_is_alive = player_1_demo_timer == 0.0

    player_0_is_alive = np.array(player_0_is_alive, dtype=np.float32).reshape(1)
    player_1_is_alive = np.array(player_1_is_alive, dtype=np.float32).reshape(1)

    player_0_speed, player_0_super_sonic = get_speed(player_0_velocity)
    player_1_speed, player_1_super_sonic = get_speed(player_1_velocity)
    ball_speed, _ = get_speed(ball_velocity)

    player_opponent_pos_diff, player_opponent_pos_norm = get_distance(player_0_pos, player_1_pos)
    player_opponent_vel_diff, player_opponent_vel_norm = get_distance(player_0_velocity, player_1_velocity)

    player_ball_pos_diff, player_ball_pos_norm = get_distance(player_0_pos, ball_pos)
    player_ball_vel_diff, player_ball_vel_norm = get_distance(player_0_velocity, ball_velocity)

    opponent_ball_pos_diff, opponent_ball_pos_norm = get_distance(player_1_pos, ball_pos)
    opponent_ball_vel_diff, opponent_ball_vel_norm = get_distance(player_1_velocity, ball_velocity)

    result = np.concatenate((
        player_car_state, opponent_car_data, pads, ball_data,
        player_opponent_pos_diff, player_opponent_pos_norm,
        player_opponent_vel_diff, player_opponent_vel_norm,
        player_ball_pos_diff, player_ball_pos_norm,
        player_ball_vel_diff, player_ball_vel_norm,
        opponent_ball_pos_diff, opponent_ball_pos_norm,
        opponent_ball_vel_diff, opponent_ball_vel_norm,
        is_boost_active,
        player_0_is_alive, player_1_is_alive,
        player_0_speed, player_0_super_sonic,
        player_1_speed, player_1_super_sonic,
        ball_speed, prev_action_enc)
    )

    return result


def get_action_encoding(y_train: np.ndarray):
    assert y_train.shape[1] == 7

    result = enc.fit_transform(y_train)

    assert result.shape[1] == 19

    return result


def zip_strict(*iterables: Iterable) -> Iterable:
    r"""
    ``zip()`` function but enforces that iterables are of equal length.
    Raises ``ValueError`` if iterables not of equal length.
    Code inspired by Stackoverflow answer for question #32954486.

    :param \*iterables: iterables to ``zip()``
    """
    # As in Stackoverflow #32954486, use
    # new object for "empty" in case we have
    # Nones in iterable.
    sentinel = object()
    for combo in zip_longest(*iterables, fillvalue=sentinel):
        if sentinel in combo:
            raise ValueError("Iterables have different lengths")
        yield combo


class SeerScaler(nn.Module):
    def __init__(self):
        super().__init__()

        player_scaler = [
            1.0 / 4096.0,
            1.0 / 5120.0,
            1.0 / 2048.0,
            1.0 / math.pi,
            1.0 / math.pi,
            1.0 / math.pi,
            1.0 / 2300.0,
            1.0 / 2300.0,
            1.0 / 2300.0,
            1.0 / 5.5,
            1.0 / 5.5,
            1.0 / 5.5,
            1.0 / 3.0,
            1.0 / 100.0,
            1.0,
            1.0,
        ]

        ball_scaler = [
            1.0 / 4096.0,
            1.0 / 5120.0,
            1.0 / 2048.0,
            1.0 / 6000.0,
            1.0 / 6000.0,
            1.0 / 6000.0,
            1.0 / 6.0,
            1.0 / 6.0,
            1.0 / 6.0,
        ]

        boost_timer_scaler = [
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 10.0,
            1.0 / 10.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 10.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 10.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 10.0,
            1.0 / 10.0,
            1.0 / 4.0,
            1.0 / 4.0,
            1.0 / 4.0,
        ]

        pos_diff = [
            1.0 / (4096.0 * 2.0),
            1.0 / (5120.0 * 2.0),
            1.0 / 2048.0,
            1.0 / 13272.55,
        ]
        vel_diff_player = [
            1.0 / (2300.0 * 2.0),
            1.0 / (2300.0 * 2.0),
            1.0 / (2300.0 * 2.0),
            1.0 / 2300.0,
        ]

        vel_diff_ball = [
            1.0 / (2300.0 + 6000.0),
            1.0 / (2300.0 + 6000.0),
            1.0 / (2300.0 + 6000.0),
            1.0 / 6000.0,
        ]

        boost_active = [
            1.0 for _ in range(34)
        ]
        player_alive = [1.0]

        player_speed = [
            1.0 / 2300,
            1.0,
        ]

        ball_speed = [
            1.0 / 6000.0
        ]

        prev_action = [1.0 for _ in range(19)]

        scaler = np.concatenate(
            [player_scaler, player_scaler, boost_timer_scaler, ball_scaler,
             pos_diff,
             vel_diff_player,
             pos_diff,
             vel_diff_ball,
             pos_diff,
             vel_diff_ball,
             boost_active,
             player_alive, player_alive,
             player_speed,
             player_speed,
             ball_speed, prev_action]
        )

        self.scaler = torch.tensor(scaler, dtype=torch.float32, requires_grad=False)

        assert torch.all(self.scaler <= 1.0)

    def forward(self, x):
        with torch.no_grad():

            if x.is_cuda:
                device_x = "cuda"
            else:
                device_x = "cpu"

            self.scaler = self.scaler.to(device_x)

            x = x * self.scaler
        return x


class SeerFeatureExtractor(nn.Module):

    def __init__(self, observation_space, net_arch: List[int] = [], activation_fn: Type[nn.Module] = None):
        super(SeerFeatureExtractor, self).__init__()

        self.scaler = SeerScaler()

        mlp_encoder = []

        for i in range(len(net_arch)):
            if isinstance(net_arch[i], int):

                if i == 0:
                    mlp_encoder.append(nn.Linear(observation_space, net_arch[i]))

                else:
                    mlp_encoder.append(nn.Linear(net_arch[i - 1], net_arch[i]))
                mlp_encoder.append(activation_fn())

            else:
                raise Exception("Expected List of ints, got {}".format(type(net_arch[i])))

        self.mlp_encoder = nn.Sequential(*mlp_encoder)

    def forward(self, observations: torch.Tensor) -> torch.Tensor:

        obs = self.scaler(observations)
        encoding = self.mlp_encoder(obs)
        return encoding


class MlpExtractor(nn.Module):
    """
    Constructs an MLP that receives the output from a previous feature extractor (i.e. a CNN) or directly
    the observations (if no feature extractor is applied) as an input and outputs a latent representation
    for the policy and a value network.
    The ``net_arch`` parameter allows to specify the amount and size of the hidden layers and how many
    of them are shared between the policy network and the value network. It is assumed to be a list with the following
    structure:

    1. An arbitrary length (zero allowed) number of integers each specifying the number of units in a shared layer.
       If the number of ints is zero, there will be no shared layers.
    2. An optional dict, to specify the following non-shared layers for the value network and the policy network.
       It is formatted like ``dict(vf=[<value layer sizes>], pi=[<policy layer sizes>])``.
       If it is missing any of the keys (pi or vf), no non-shared layers (empty list) is assumed.

    For example to construct a network with one shared layer of size 55 followed by two non-shared layers for the value
    network of size 255 and a single non-shared layer of size 128 for the policy network, the following layers_spec
    would be used: ``[55, dict(vf=[255, 255], pi=[128])]``. A simple shared network topology with two layers of size 128
    would be specified as [128, 128].

    Adapted from Stable Baselines.

    :param feature_dim: Dimension of the feature vector (can be the output of a CNN)
    :param net_arch: The specification of the policy and value networks.
        See above for details on its formatting.
    :param activation_fn: The activation function to use for the networks.
    :param device:
    """

    def __init__(
            self,
            feature_dim: int,
            net_arch: List[Union[int, Dict[str, List[int]]]],
            activation_fn: Type[nn.Module],
            device: Union[torch.device, str] = "cpu",
    ):
        super(MlpExtractor, self).__init__()
        shared_net, policy_net, value_net = [], [], []
        policy_only_layers = []  # Layer sizes of the network that only belongs to the policy network
        value_only_layers = []  # Layer sizes of the network that only belongs to the value network
        last_layer_dim_shared = feature_dim

        # Iterate through the shared layers and build the shared parts of the network
        for layer in net_arch:
            if isinstance(layer, int):  # Check that this is a shared layer
                shared_net.append(nn.Linear(last_layer_dim_shared, layer))  # add linear of size layer
                shared_net.append(activation_fn())
                last_layer_dim_shared = layer
            else:
                assert isinstance(layer, dict), "Error: the net_arch list can only contain ints and dicts"
                if "pi" in layer:
                    assert isinstance(layer["pi"], list), "Error: net_arch[-1]['pi'] must contain a list of integers."
                    policy_only_layers = layer["pi"]

                if "vf" in layer:
                    assert isinstance(layer["vf"], list), "Error: net_arch[-1]['vf'] must contain a list of integers."
                    value_only_layers = layer["vf"]
                break  # From here on the network splits up in policy and value network

        last_layer_dim_pi = last_layer_dim_shared
        last_layer_dim_vf = last_layer_dim_shared

        # Build the non-shared part of the network
        for pi_layer_size, vf_layer_size in zip_longest(policy_only_layers, value_only_layers):
            if pi_layer_size is not None:
                assert isinstance(pi_layer_size, int), "Error: net_arch[-1]['pi'] must only contain integers."
                policy_net.append(nn.Linear(last_layer_dim_pi, pi_layer_size))
                policy_net.append(activation_fn())
                last_layer_dim_pi = pi_layer_size

            if vf_layer_size is not None:
                assert isinstance(vf_layer_size, int), "Error: net_arch[-1]['vf'] must only contain integers."
                value_net.append(nn.Linear(last_layer_dim_vf, vf_layer_size))
                value_net.append(activation_fn())
                last_layer_dim_vf = vf_layer_size

        # Save dim, used to create the distributions
        self.latent_dim_pi = last_layer_dim_pi
        self.latent_dim_vf = last_layer_dim_vf

        # Create networks
        # If the list of layers is empty, the network will just act as an Identity module
        self.shared_net = nn.Sequential(*shared_net).to(device)
        self.policy_net = nn.Sequential(*policy_net).to(device)
        self.value_net = nn.Sequential(*value_net).to(device)

    def forward(self, features: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        :return: latent_policy, latent_value of the specified network.
            If all layers are shared, then ``latent_policy == latent_value``
        """
        shared_latent = self.shared_net(features)
        return self.policy_net(shared_latent), self.value_net(shared_latent)

    def forward_actor(self, features: torch.Tensor) -> torch.Tensor:
        return self.policy_net(self.shared_net(features))

    def forward_critic(self, features: torch.Tensor) -> torch.Tensor:
        return self.value_net(self.shared_net(features))


def make_proba_distribution(
        action_space, use_sde: bool = False, dist_kwargs: Optional[Dict[str, Any]] = None
):
    """
    Return an instance of Distribution for the correct type of action space

    :param action_space: the input action space
    :param use_sde: Force the use of StateDependentNoiseDistribution
        instead of DiagGaussianDistribution
    :param dist_kwargs: Keyword arguments to pass to the probability distribution
    :return: the appropriate Distribution object
    """
    # if dist_kwargs is None:
    #     dist_kwargs = {}
    return MultiCategoricalDistribution(action_space)


class MultiCategoricalDistribution:
    """
    MultiCategorical distribution for multi discrete actions.

    :param action_dims: List of sizes of discrete action spaces
    """

    def __init__(self, action_dims: List[int]):
        super(MultiCategoricalDistribution, self).__init__()
        self.distribution = None
        self.action_dims = action_dims

    def proba_distribution_net(self, latent_dim: int) -> nn.Module:
        """
        Create the layer that represents the distribution:
        it will be the logits (flattened) of the MultiCategorical distribution.
        You can then get probabilities using a softmax on each sub-space.

        :param latent_dim: Dimension of the last layer
            of the policy network (before the action layer)
        :return:
        """

        action_logits = nn.Linear(latent_dim, int(sum(self.action_dims)))
        return action_logits

    def proba_distribution(self, action_logits: torch.Tensor) -> "MultiCategoricalDistribution":
        self.distribution = [Categorical(logits=split, validate_args=False) for split in torch.split(action_logits, tuple(self.action_dims), dim=1)]
        return self

    def log_prob(self, actions: torch.Tensor) -> torch.Tensor:
        # Extract each discrete action and compute log prob for their respective distributions
        return torch.stack(
            [dist.log_prob(action) for dist, action in zip(self.distribution, torch.unbind(actions, dim=1))], dim=1
        ).sum(dim=1)

    def entropy(self) -> torch.Tensor:
        return torch.stack([dist.entropy() for dist in self.distribution], dim=1).sum(dim=1)

    def sample(self) -> torch.Tensor:
        return torch.stack([dist.sample() for dist in self.distribution], dim=1)

    def mode(self) -> torch.Tensor:
        return torch.stack([torch.argmax(dist.probs, dim=1) for dist in self.distribution], dim=1)

    def actions_from_params(self, action_logits: torch.Tensor, deterministic: bool = False) -> torch.Tensor:
        # Update the proba distribution
        self.proba_distribution(action_logits)
        return self.get_actions(deterministic=deterministic)

    def log_prob_from_params(self, action_logits: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        actions = self.actions_from_params(action_logits)
        log_prob = self.log_prob(actions)
        return actions, log_prob

    def get_actions(self, deterministic: bool = False) -> torch.Tensor:
        """
        Return actions according to the probability distribution.

        :param deterministic:
        :return:
        """
        if deterministic:
            return self.mode()
        return self.sample()


class Seer_Network(nn.Module):

    def __init__(self):
        super(Seer_Network, self).__init__()

        self.features_extractor = SeerFeatureExtractor(159, [256], nn.LeakyReLU)
        self.lstm_actor = nn.LSTM(256, 512, num_layers=1)
        self.lstm_critic = None
        self.shared_lstm = True
        self.HUGE_NEG = torch.tensor(-1e8, dtype=torch.float32)

        self.mlp_extractor = MlpExtractor(
            512,
            net_arch=[dict(vf=[256, 128], pi=[256, 256, 128])],
            activation_fn=nn.LeakyReLU,
            device="cpu",
        )
        flip_bins = 5
        throttle_bins = 3
        roll_bins = 3
        self.value_net = nn.Linear(self.mlp_extractor.latent_dim_vf, 1)
        action_space = [throttle_bins] + [flip_bins] * 2 + [roll_bins] + [2] * 3
        self.action_dist = make_proba_distribution(action_space, use_sde=False, dist_kwargs=None)

        latent_dim_pi = self.mlp_extractor.latent_dim_pi

        if isinstance(self.action_dist, MultiCategoricalDistribution):
            self.action_net = self.action_dist.proba_distribution_net(latent_dim=latent_dim_pi)
        else:
            raise NotImplementedError(f"Unsupported distribution '{self.action_dist}'.")

    @staticmethod
    def _process_sequence(
            features: torch.Tensor,
            lstm_states: Tuple[torch.Tensor, torch.Tensor],
            episode_starts: torch.Tensor,
            lstm: nn.LSTM,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        # LSTM logic
        # (sequence length, n_envs, features dim) (batch size = n envs)
        n_envs = lstm_states[0].shape[1]
        # Batch to sequence
        features_sequence = features.reshape((n_envs, -1, lstm.input_size)).swapaxes(0, 1)
        episode_starts = episode_starts.reshape((n_envs, -1)).swapaxes(0, 1)

        # print("features_sequence: ", features_sequence.shape)

        if torch.all(episode_starts == 0.0):
            hidden_eff, lstm_states_eff = lstm(features_sequence, lstm_states)
            hidden_eff = torch.flatten(hidden_eff.transpose(0, 1), start_dim=0, end_dim=1)
            return hidden_eff, lstm_states_eff

        lstm_output = []
        # Iterate over the sequence
        for features, episode_start in zip_strict(features_sequence, episode_starts):
            hidden, lstm_states = lstm(
                features.unsqueeze(dim=0),
                (
                    (1.0 - episode_start).view(1, n_envs, 1) * lstm_states[0],
                    (1.0 - episode_start).view(1, n_envs, 1) * lstm_states[1],
                ),
            )
            lstm_output += [hidden]
        # Sequence to batch
        lstm_output = torch.flatten(torch.cat(lstm_output).transpose(0, 1), start_dim=0, end_dim=1)
        return lstm_output, lstm_states

    def forward(
            self,
            obs: torch.Tensor,
            lstm_states: Tuple[torch.Tensor, torch.Tensor],
            episode_starts: torch.Tensor,
            deterministic: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Forward pass in all torche networks (actor and critic)

        :param obs: Observation. Observation
        :param lstm_states: torche last hidden and memory states for torche LSTM.
        :param episode_starts: Whetorcher torche observations correspond to new episodes
            or not (we reset torche lstm states in torchat case).
        :param deterministic: Whetorcher to sample or use deterministic actions
        :return: action, value and log probability of torche action
        """
        # Preprocess torche observation if needed
        features = self.extract_features(obs)
        # latent_pi, latent_vf = self.mlp_extractor(features)
        latent_pi, lstm_states_pi = self._process_sequence(features, lstm_states, episode_starts, self.lstm_actor)
        if self.lstm_critic is not None:
            # latent_vf, lstm_states_vf = self._process_sequence(features, lstm_states.vf, episode_starts, self.lstm_critic)
            pass
        elif self.shared_lstm:
            # Re-use LSTM features but do not backpropagate
            latent_vf = latent_pi
            lstm_states_vf = (lstm_states_pi[0], lstm_states_pi[1])
        else:
            latent_vf = self.critic(features)
            lstm_states_vf = lstm_states_pi

        latent_pi = self.mlp_extractor.forward_actor(latent_pi)
        latent_vf = self.mlp_extractor.forward_critic(latent_vf)

        # Evaluate torche values for torche given observations
        values = self.value_net(latent_vf)
        distribution = self._get_action_dist_from_latent(latent_pi, obs)
        actions = distribution.get_actions(deterministic=deterministic)
        log_prob = distribution.log_prob(actions)
        return actions, values, log_prob, lstm_states_pi

    def extract_features(self, obs):
        return self.features_extractor(obs)

    def _get_action_dist_from_latent(self, latent_pi: torch.Tensor, obs: torch.Tensor = None):
        """
        Retrieve action distribution given the latent codes.

        :param latent_pi: Latent code for the actor
        :return: Action distribution
        """
        mean_actions = self.action_net(latent_pi)

        if self.HUGE_NEG is None:
            self.HUGE_NEG = torch.tensor(-1e8, dtype=torch.float32).to(self.device)

        if obs is not None:
            assert obs.size(1) == 159
            assert mean_actions.size(1) == 22

            has_boost = obs[:, 13] > 0.0
            on_ground = obs[:, 14]
            has_flip = obs[:, 15]

            not_on_ground = torch.logical_not(on_ground)
            mask = torch.ones_like(mean_actions, dtype=torch.bool)

            # mask[:, 0:3] = 1.0  # Throttle, always possible
            # mask[:, 3:8] = 1.0  # Steer yaw, always possible
            # mask[:, 8:13] = 1.0  # pitch, not on ground but (flip resets, walldashes)
            # mask[:, 13:16] = 1.0  # roll, not on ground
            # mask[:, 16:18] = 1.0  # jump, has flip (turtle)
            # mask[:, 18:20] = 1.0  # boost, boost > 0
            # mask[:, 20:22] = 1.0  # Handbrake, at least one wheel ground (not doable)

            mask[:, 0] = on_ground  # throttle -1
            # mask[:, 2] = on_ground  # throttle 1

            mask[:, 8] = not_on_ground  # pitch -1
            mask[:, 9] = not_on_ground  # pitch -0.5
            mask[:, 11] = not_on_ground  # pitch 0.5
            mask[:, 12] = not_on_ground  # pitch 1.0

            mask[:, 13] = not_on_ground  # roll -1
            mask[:, 15] = not_on_ground  # roll 1

            mask[:, 17] = has_flip  # Jump
            mask[:, 19] = has_boost  # boost

            mask[:, 21] = on_ground  # Handbrake

            mean_actions = torch.where(mask, mean_actions, self.HUGE_NEG)

        if isinstance(self.action_dist, MultiCategoricalDistribution):
            # Here mean_actions are the flattened logits
            return self.action_dist.proba_distribution(action_logits=mean_actions)
        else:
            raise ValueError("Invalid action distribution")
