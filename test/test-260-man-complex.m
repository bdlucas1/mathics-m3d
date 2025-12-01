(* Use the sliders to move the poles and zeros *)
Manipulate[
    ComplexPlot[
        ((z + I - z1) (z - I - z2)) / ((z - 1 + I p1) (z + 1 + I p2)),
        {z, -2 - 2 I, 2 + 2 I}
    ],
    {{z1,0}, -1.0, 1.0, 0.05},
    {{z2,0}, -1.0, 1.0, 0.05},
    {{p1,0}, -1.0, 1.0, 0.05},
    {{p2,0}, -1.0, 1.0, 0.05}
]
