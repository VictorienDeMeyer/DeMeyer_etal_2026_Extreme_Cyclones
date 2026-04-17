# module load gcc netcdf-fortran
# compile with "make tracks"

EBROOTNETCDFMINFORTRAN = /cvmfs/soft.computecanada.ca/easybuild/software/2020/avx2/Compiler/gcc9/netcdf-fortran/4.6.0
FC = gfortran
FFLAGS = $(nf-config --fflags) -I$(EBROOTNETCDFMINFORTRAN)/include
LDPATH = $(nf-config --flibs)
LIBS   = -lnetcdf -lnetcdff

storm_tracks.o: storm_tracks.f90 input_args.cdk io_files_cdf_mod.o read_args_mod.o
	$(FC) $(FFLAGS) -o $@ -c $<

read_args_mod.o: read_args_mod.f90 input_args.cdk
	$(FC) $(FFLAGS) -o $@ -c $<

io_files_cdf_mod.o: io_files_cdf_mod.f90 read_args_mod.o
	$(FC) $(FFLAGS) -o $@ -c $<

tracks: storm_tracks.o read_args_mod.o io_files_cdf_mod.o
	$(FC) $(LDPATH) -o storm_tracks.Abs storm_tracks.o read_args_mod.o io_files_cdf_mod.o $(LIBS)

clean:
	-rm -f *.o *.mod
