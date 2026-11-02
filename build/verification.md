# iPhone Duo CAD vs drawing (sheet 1 of 7)

Measured from `build/iPhone_Duo.step`. Units mm.

| Feature | Drawing | Model | Δ | OK | Note |
|---|---|---|---|---|---|
| Product width (hinge exterior to edge) | 84.100 | 84.100 | +0.000 | ✓ |  |
| Product length | 117.800 | 117.803 | +0.003 | ✓ |  |
| Product thickness (section at y = -80) | 11.300 | 11.301 | +0.001 | ✓ |  |
| Half A thickness | 5.480 | 5.480 | +0.000 | ✓ |  |
| Back plate to camera plateau | 3.640 | 3.640 | +0.000 | ✓ |  |
| Back plate to rear camera glass | 5.720 | 5.720 | -0.000 | ✓ |  |
| Detail A corner: worst of 7 points off the outline | 0.000 | 0.003 | +0.003 | ✓ |  |
| Detail AY body corner: worst of 4 points | 0.000 | 0.000 | +0.000 | ✓ |  |
| Detail AY barrel end: worst of 3 points | 0.000 | 0.005 | +0.005 | ✓ |  |
| Barrel end from top edge (Detail AY) | 1.190 | 1.190 | -0.000 | ✓ |  |
| Barrel end from top edge (side view) | 1.230 | 1.190 | -0.040 | drawing conflict | sheet says 1.19 in Detail AY, 1.23 in the side view; model uses 1.19 |
| Barrel top from front face (side view 1.55) | 1.550 | 1.560 | +0.010 | ✓ |  |
| Detail B edge round: worst of 12 points | 0.000 | 0.000 | +0.000 | ✓ |  |
| Detail E barrel: worst of 10 points | 0.000 | 0.010 | +0.010 | ✓ |  |
| Detail E hinge-side round: worst of 8 points | 0.000 | 0.002 | +0.002 | ✓ |  |
| Cover glass width | 79.930 | 79.930 | +0.000 | ✓ |  |
| Cover glass length | 115.040 | 115.043 | +0.003 | ✓ |  |
| Exterior of housing to cover glass (right) | 1.330 | 1.380 | +0.050 | drawing conflict | callout and the 115.04 glass size disagree by 0.05; size wins |
| Display active area width | 77.170 | 77.170 | +0.000 | ✓ |  |
| Display active area length | 112.280 | 112.283 | +0.003 | ✓ |  |
| Exterior of housing to display active area | 2.710 | 2.760 | +0.050 | drawing conflict | 2.71 callout and the 112.28 size disagree by 0.05; size wins |
| Exterior of hinge to display active area | 4.130 | 4.170 | +0.040 | drawing conflict | 4.13 + 77.17 + 2.71 = 84.01, not 84.10; size wins |
| Exterior of hinge to start of flat area | 4.160 | 2.740 | -1.420 | drawing conflict | Detail E puts the flat at 2.74 from the hinge exterior; model follows Detail E |
| Front camera X | 73.390 | 73.390 | +0.000 | ✓ |  |
| Front camera Y | 10.620 | 10.620 | +0.000 | ✓ |  |
| Front camera diameter | 6.070 | 6.070 | -0.000 | ✓ |  |
| B_volume_down centre X | 44.350 | 44.350 | -0.000 | ✓ |  |
| B_volume_down length | 10.880 | 10.880 | +0.000 | ✓ |  |
| B_volume_down proud of top edge | 0.450 | 0.450 | +0.000 | ✓ |  |
| B_volume_up centre X | 57.730 | 57.730 | +0.000 | ✓ |  |
| B_volume_up length | 10.880 | 10.880 | +0.000 | ✓ |  |
| B_volume_up proud of top edge | 0.450 | 0.450 | +0.000 | ✓ |  |
| B_side_button centre Y | 42.870 | 42.870 | +0.000 | ✓ |  |
| B_side_button length (2x 9.34) | 18.680 | 18.680 | +0.000 | ✓ |  |
| B_side_button width | 3.060 | 3.060 | -0.000 | ✓ |  |
| B_side_button proud of side | 0.450 | 0.450 | +0.000 | ✓ |  |
| B_side_button centre from back face | 2.670 | 2.670 | +0.000 | ✓ |  |
| B_camera_control centre Y | 84.970 | 84.970 | +0.000 | ✓ |  |
| B_camera_control length (2x 8.55) | 17.100 | 17.100 | +0.000 | ✓ |  |
| B_camera_control width | 2.530 | 2.530 | +0.000 | ✓ |  |
| B_camera_control proud of side | 0.075 | 0.075 | +0.000 | ✓ |  |
| B_camera_control centre from back face | 2.670 | 2.670 | +0.000 | ✓ |  |
| Rear camera at 15.25: X from edge | 15.250 | 15.250 | +0.000 | ✓ |  |
| Rear camera at 15.25: Y | 15.250 | 15.250 | +0.000 | ✓ |  |
| Rear camera at 15.25: diameter | 16.200 | 16.200 | -0.000 | ✓ |  |
| Rear camera at 32.98: X from edge | 32.980 | 32.980 | +0.000 | ✓ |  |
| Rear camera at 32.98: Y | 15.250 | 15.250 | +0.000 | ✓ |  |
| Rear camera at 32.98: diameter | 16.200 | 16.200 | +0.000 | ✓ |  |
| Flash X from edge | 49.580 | 49.580 | -0.000 | ✓ |  |
| Flash Y | 19.700 | 19.700 | +0.000 | ✓ |  |
| Flash diameter | 3.750 | 3.750 | +0.000 | ✓ |  |
| Plateau top, X from edge (near) | 4.940 | 4.940 | +0.000 | ✓ |  |
| Plateau top, X from edge (far) | 60.560 | 60.560 | -0.000 | ✓ |  |
| Plateau top, upper edge Y | 4.700 | 4.700 | -0.000 | ✓ |  |
| Plateau top, lower edge Y | 25.800 | 25.800 | +0.000 | ✓ |  |
| Plateau base, X from edge (far) | 69.370 | 69.365 | -0.005 | ✓ |  |
| Plateau base, lower edge Y | 34.620 | 34.605 | -0.015 | ✓ |  |
| Rear mic opening at (49.58, 10.95) | hole | hole | | ✓ |  |
| Port Ø1.53 at 17.78 | hole | hole | | ✓ |  |
| Port Ø1.53 at 20.03 | hole | hole | | ✓ |  |
| Port Ø1.53 at 22.29 | hole | hole | | ✓ |  |
| Port Ø1.53 at 24.54 | hole | hole | | ✓ |  |
| Port Ø1.53 at 60.85 | hole | hole | | ✓ |  |
| Port Ø1.53 at 63.10 | hole | hole | | ✓ |  |
| Port Ø1.53 at 65.36 | hole | hole | | ✓ |  |
| Port Ø1.53 at 67.61 | hole | hole | | ✓ |  |
| USB-C opening left end at 38.42 | edge | edge | | ✓ | 8.59 wide slot centred on 42.70 |
| USB-C opening right end at 46.99 | edge | edge | | ✓ | 8.59 wide slot centred on 42.70 |
| A screw at 35.35 | 35.350 | 35.350 | +0.000 | ✓ |  |
| A screw at 50.04 | 50.040 | 50.040 | +0.000 | ✓ |  |
| B screw at 35.35 | 35.350 | 35.350 | +0.000 | ✓ |  |
| B screw at 50.04 | 50.040 | 50.040 | +0.000 | ✓ |  |

67/67 checks within tolerance (0.02 mm unless noted); 5 places where the sheet contradicts itself are listed as conflicts.
