from typing import Tuple

import torch
from torch import nn

from utils.train_constants import VAE_Z_SIZE, IMG_SIZE


class VAE(nn.Module):
    def __init__(self):
        super().__init__()

        self.conv_encoder = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=16, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(num_features=16),
            nn.LeakyReLU(negative_slope=0.2),

            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(num_features=32),
            nn.LeakyReLU(negative_slope=0.2),

            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(negative_slope=0.2),

            nn.Conv2d(in_channels=64, out_channels=128, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(negative_slope=0.2),

            nn.Conv2d(in_channels=128, out_channels=256, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(negative_slope=0.2),

            nn.Conv2d(in_channels=256, out_channels=512, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(negative_slope=0.2),
        )

        self.linear_encoder = nn.Sequential(
            nn.Linear(in_features=8192, out_features=1000),
            nn.BatchNorm1d(1000),
            nn.ReLU(),
        )

        self.mu_encoder = nn.Linear(1000, VAE_Z_SIZE)
        self.log_var_encoder = nn.Linear(1000, VAE_Z_SIZE)

        self.linear_decoder = nn.Sequential(
            nn.Linear(in_features=VAE_Z_SIZE, out_features=512 * 5 * 5),
            nn.BatchNorm1d(512 * 5 * 5),
            nn.LeakyReLU(negative_slope=0.2)
        )

        self.conv_decoder = nn.Sequential(

            nn.ConvTranspose2d(in_channels=512, out_channels=256, kernel_size=3, stride=2),
            nn.BatchNorm2d(num_features=256),
            nn.LeakyReLU(negative_slope=0.2),

            nn.ConvTranspose2d(in_channels=256, out_channels=128, kernel_size=3, stride=2),
            nn.BatchNorm2d(num_features=128),
            nn.LeakyReLU(negative_slope=0.2),

            nn.ConvTranspose2d(in_channels=128, out_channels=64, kernel_size=3, stride=2, output_padding=1),
            nn.BatchNorm2d(num_features=64),
            nn.LeakyReLU(negative_slope=0.2),

            nn.ConvTranspose2d(in_channels=64, out_channels=32, kernel_size=3, stride=2, output_padding=1),
            nn.BatchNorm2d(num_features=32),
            nn.LeakyReLU(negative_slope=0.2),

            nn.ConvTranspose2d(in_channels=32, out_channels=3, kernel_size=3, stride=1),
            nn.Tanh()
        )

    def forward(self, x):
        mu, log_var = self.encode(x)
        z = VAE.parametrize(mu, log_var)
        return self.decode(z), mu, log_var

    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        b_size = x.size(0)
        x = self.conv_encoder(x)
        x = x.view(b_size, -1)
        x = self.linear_encoder(x)
        return self.mu_encoder(x), self.log_var_encoder(x)

    def decode(self, x: torch.Tensor):
        x = self.linear_decoder(x)
        x = x.view(-1, 512, 5, 5)
        x = self.conv_decoder(x)
        return x.view(-1, 3, IMG_SIZE, IMG_SIZE)

    @staticmethod
    def parametrize(mu, log_var):
        std = log_var.mul(0.5).exp_()
        eps = std.data.new(std.size()).normal_()
        return eps.mul(std).add_(mu)
