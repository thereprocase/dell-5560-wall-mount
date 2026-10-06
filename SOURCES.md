# Sources and image attribution

The assembly renders, exploded view, print-orientation figures and section figures were generated from this project's CAD. The CFD figure uses calculated OpenFOAM fields. They are not photographs of a printed prototype.

## Dell reference material

Dell owns the manufacturer reference imagery. It appears here for geometry identification and annotated comparison; it is not original project artwork or a dimensioned factory CAD model. No blanket project license grants rights to Dell imagery, documentation or trademarks.

- [Precision 5560 setup and specifications](https://dl.dell.com/content/manual34721296-precision-5560-setup-and-specifications.pdf?language=en-us).
- [Precision 5560 service manual](https://dl.dell.com/content/manual44781765-precision-5560-service-manual.pdf?language=en-us).
- [Right-side source image](https://dl.dell.com/content/guides/public/html//prec5560_ss/images/GUID-C9E741CA-573F-4F5F-85BB-CD9ECC09733B-low.jpg): `reference/Dell_5560_Right.jpg` and the scaled/annotated profile figure.
- [Left-side source image](https://dl.dell.com/content/guides/public/html//prec5560_ss/images/GUID-F3D2233E-BA0B-4F18-8844-6073DA79A323-low.jpg): `reference/Dell_5560_Left.jpg`.
- [Inside base-cover source image](https://dl.dell.com/content/guides/public/Html/prec5560_sm/images/GUID-D9E7DDF5-01D6-4E98-B3FB-83A574C6A4BE-low.jpg): `reference/Dell_5560_Base_Inside.jpg` and the annotated intake-window figure.

The bottom-view reference was extracted from the setup documentation. `profile_reconstruction.json` preserves source hashes and manual picks. Width and depth establish the image scale; the silhouette, foot projection and intake locations remain estimates. Full manufacturer PDFs are linked instead of duplicated in this repository.

## Numerical and printing references

- [OpenFOAM k–omega SST documentation](https://doc.openfoam.com/2306/tools/processing/models/turbulence/ras/linear-evm/rtm/kOmegaSST/). This is explanatory documentation; the actual solver used was v1912, as recorded with the cases.
- [OpenFOAM boundary conditions](https://www.openfoam.com/documentation/user-guide/a-reference/a.4-standard-boundary-conditions).
- [Bambu ASA guidance](https://bambulab.com/en-us/filament/asa).
- [Bambu print-volume limitations](https://wiki.bambulab.com/en/knowledge-sharing/print-volume-limitations).
- [Bambu Studio 2.8.2.61 profile sources](https://github.com/bambulab/BambuStudio/tree/v02.08.02.61/resources/profiles/BBL).
- [Prusa adhesive and assembly guidance](https://blog.prusa3d.com/the-great-guide-to-gluing-and-assembling-3d-prints_44908/).

The cited guidance informs the starting process. Actual spool behavior, bond preparation, printer calibration and service temperatures still need prototype verification.
